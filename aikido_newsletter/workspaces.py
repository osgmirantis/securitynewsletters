"""
Multi-workspace configuration.

Aikido API credentials are scoped to a single workspace, so covering several
workspaces means one Client ID/Secret per workspace. Define them via the
AIKIDO_WORKSPACES env var (JSON), each entry referencing its own secret env
vars so secrets stay separate (recommended for CI):

  AIKIDO_WORKSPACES='[
    {"name":"Platform","region":"eu","id_env":"AIK_ID_PLATFORM","secret_env":"AIK_SECRET_PLATFORM"},
    {"name":"Data","region":"us","id_env":"AIK_ID_DATA","secret_env":"AIK_SECRET_DATA"}
  ]'

Inline `client_id`/`client_secret` are also accepted. If AIKIDO_WORKSPACES is
unset, falls back to a single workspace from AIKIDO_CLIENT_ID/SECRET/REGION.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass


@dataclass
class Workspace:
    name: str
    region: str
    client_id: str
    client_secret: str
    prefix: str | None = None  # None => global default; "" => all teams (e.g. MOSK)


def presence() -> str:
    """Report which credential env vars are visible, without leaking values."""
    def st(n: str) -> str:
        v = os.environ.get(n)
        return "set" if v else ("EMPTY" if v == "" else "unset")
    return (f"AIKIDO_WORKSPACES={st('AIKIDO_WORKSPACES')}, "
            f"AIKIDO_CLIENT_ID={st('AIKIDO_CLIENT_ID')}, "
            f"AIKIDO_CLIENT_SECRET={st('AIKIDO_CLIENT_SECRET')}")


def load() -> list[Workspace]:
    raw = os.environ.get("AIKIDO_WORKSPACES")
    if raw:
        out: list[Workspace] = []
        for e in json.loads(raw):
            cid = e.get("client_id") or os.environ.get(e.get("id_env", ""))
            sec = e.get("client_secret") or os.environ.get(e.get("secret_env", ""))
            if not (cid and sec):
                raise SystemExit(
                    f"Workspace {e.get('name', '?')!r}: missing client_id/secret "
                    f"(checked inline and env {e.get('id_env')}/{e.get('secret_env')})."
                )
            prefix = e.get("prefix")            # explicit per-workspace override
            if e.get("all_teams"):              # convenience flag => take every team
                prefix = ""
            out.append(Workspace(e["name"], e.get("region", "eu"), cid, sec, prefix))
        if not out:
            raise SystemExit("AIKIDO_WORKSPACES is empty.")
        return out

    cid = os.environ.get("AIKIDO_CLIENT_ID")
    sec = os.environ.get("AIKIDO_CLIENT_SECRET")
    if cid and sec:
        return [Workspace(
            os.environ.get("WORKSPACE_NAME", "default"),
            os.environ.get("AIKIDO_REGION", "eu"), cid, sec)]
    return []
