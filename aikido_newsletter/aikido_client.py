"""
Thin client for the Aikido Security public REST API.

Auth model (per https://apidocs.aikido.dev/reference/authorization):
  Aikido uses OAuth2 *client credentials*. You create a Client ID + Client Secret
  in Aikido under Settings -> Integrations -> API, with the scopes:
      teams:read   issues:read
  Those are exchanged here for a short-lived Bearer access token.

Only two endpoints are needed for the newsletter:
  GET /teams            -> list teams (paginated, per_page max 20)
  GET /issues/export    -> full issue export, supports filter_team_id
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass, field
from typing import Any

import requests

# Regional hosts. Aikido data is region-pinned; pick the one your workspace lives in.
_REGIONS = {
    "eu": "https://app.aikido.dev",
    "us": "https://app.us.aikido.dev",
    "me": "https://app.me.aikido.dev",
}


@dataclass
class Team:
    id: int
    name: str
    active: bool
    responsibilities: list[dict] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


class AikidoError(RuntimeError):
    pass


class AikidoClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        region: str = "eu",
        *,
        timeout: int = 60,
        max_retries: int = 4,
    ) -> None:
        if region not in _REGIONS:
            raise ValueError(f"region must be one of {list(_REGIONS)}, got {region!r}")
        self._client_id = client_id
        self._client_secret = client_secret
        self._base = f"{_REGIONS[region]}/api/public/v1"
        self._token_url = f"{_REGIONS[region]}/api/oauth/token"
        self._timeout = timeout
        self._max_retries = max_retries
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._session = requests.Session()

    # ---- auth ---------------------------------------------------------------
    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 30:
            return self._token
        basic = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode()
        ).decode()
        resp = self._session.post(
            self._token_url,
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={"grant_type": "client_credentials"},
            timeout=self._timeout,
        )
        if resp.status_code != 200:
            raise AikidoError(
                f"Token request failed ({resp.status_code}): {resp.text[:300]}"
            )
        body = resp.json()
        self._token = body["access_token"]
        self._token_expires_at = time.time() + int(body.get("expires_in", 600))
        return self._token

    # ---- low-level GET with retry/backoff -----------------------------------
    def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self._base}{path}"
        for attempt in range(self._max_retries):
            resp = self._session.get(
                url,
                headers={
                    "Authorization": f"Bearer {self._access_token()}",
                    "Accept": "application/json",
                },
                params=params or {},
                timeout=self._timeout,
            )
            if resp.status_code == 429:  # rate limited -> honour Retry-After
                wait = int(resp.headers.get("Retry-After", 2 ** attempt))
                time.sleep(min(wait, 30))
                continue
            if resp.status_code == 401:  # token expired mid-run -> refresh once
                self._token = None
                if attempt == 0:
                    continue
            if resp.status_code >= 400:
                raise AikidoError(
                    f"GET {path} failed ({resp.status_code}): {resp.text[:300]}"
                )
            return resp.json()
        raise AikidoError(f"GET {path} exhausted retries")

    # ---- endpoints ----------------------------------------------------------
    def list_teams(self) -> list[Team]:
        teams: list[Team] = []
        page = 0
        while True:
            batch = self._get("/teams", {"page": page, "per_page": 20})
            if not batch:
                break
            for t in batch:
                teams.append(
                    Team(
                        id=t["id"],
                        name=t["name"],
                        active=t.get("active", True),
                        responsibilities=t.get("responsibilities", []),
                        raw=t,
                    )
                )
            if len(batch) < 20:
                break
            page += 1
        return teams

    def product_teams(self, prefix: str = "Product:") -> list[Team]:
        """Teams whose name starts with the product prefix (case-insensitive)."""
        p = prefix.lower()
        return [
            t for t in self.list_teams()
            if t.active and t.name.lower().startswith(p)
        ]

    def export_issues(
        self, team_id: int | None = None, status: str = "all"
    ) -> list[dict]:
        """Full issue export, optionally scoped to one team."""
        params: dict[str, Any] = {"format": "json", "filter_status": status}
        if team_id is not None:
            params["filter_team_id"] = team_id
        data = self._get("/issues/export", params)
        return data if isinstance(data, list) else data.get("issues", [])

    def issues_by_product(
        self, prefix: str = "Product:", status: str = "all"
    ) -> dict[str, list[dict]]:
        """Map of product display-name -> issues for each matching team.

        prefix="" (or None) matches every team — used for workspaces like MOSK
        whose teams don't follow the `Product:` convention.
        """
        out: dict[str, list[dict]] = {}
        for team in self.product_teams(prefix or ""):
            out[display_name(team.name, prefix or "")] = self.export_issues(
                team_id=team.id, status=status)
        return out


def display_name(team_name: str, prefix: str) -> str:
    """Strip the product prefix for display; fall back to the full team name
    (e.g. MOSK teams that have no `Product:` prefix)."""
    if prefix and team_name.lower().startswith(prefix.lower()):
        return team_name[len(prefix):].strip(" :") or team_name
    return team_name
