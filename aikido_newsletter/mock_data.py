"""
Deterministic synthetic data matching Aikido's /issues/export schema, so the
pipeline can be exercised and previewed without live credentials.
Used only when --mock is passed.
"""

from __future__ import annotations

import random
import time

DAY = 86400

_PRODUCTS = {
    "Checkout":  {"repos": ["checkout-web", "checkout-api", "payments-lib"], "lang": "TS", "vol": 1.0},
    "Payments":  {"repos": ["payments-core", "ledger-svc"], "lang": "Java", "vol": 0.8},
    "Identity":  {"repos": ["auth-gateway", "sso-svc", "user-api"], "lang": "GO", "vol": 0.7},
    "Mobile":    {"repos": ["mobile-ios", "mobile-android"], "lang": "Swift", "vol": 0.5},
}

_RULES = {
    "sast": [("SQL injection", ["CWE-89"]), ("Cross-site scripting", ["CWE-79"]),
             ("Hardcoded credentials", ["CWE-798"]), ("Path traversal", ["CWE-22"]),
             ("Insecure deserialization", ["CWE-502"]), ("SSRF", ["CWE-918"])],
    "open_source": [("Prototype pollution in lodash", ["CWE-1321"]),
                    ("RCE in log4j", ["CWE-502", "CWE-917"]),
                    ("ReDoS in semver", ["CWE-1333"]),
                    ("Auth bypass in next-auth", ["CWE-287"])],
    "leaked_secret": [("AWS access key committed", ["CWE-798"]),
                      ("Stripe live key in source", ["CWE-798"])],
    "iac": [("S3 bucket public read", ["CWE-732"]),
            ("Security group 0.0.0.0/0 :22", ["CWE-284"]),
            ("EKS public endpoint", ["CWE-284"])],
    "docker_container": [("CVE in base image openssl", ["CWE-327"]),
                         ("Root user in container", ["CWE-250"])],
    "cloud": [("IAM role with *:* policy", ["CWE-269"]),
              ("Unencrypted RDS instance", ["CWE-311"])],
}
_PKGS = ["lodash", "log4j-core", "semver", "next-auth", "minimist", "axios", "jackson-databind"]
_CVES = ["CVE-2021-44228", "CVE-2022-24999", "CVE-2023-26136", "CVE-2024-21626", "CVE-2021-23337"]
_SEV = ["critical", "high", "medium", "low"]
_SEV_W = [0.12, 0.28, 0.4, 0.2]
_SLA_DAYS = {"critical": 7, "high": 14, "medium": 30, "low": 90}


def _score(sev: str, rng: random.Random) -> int:
    base = {"critical": 88, "high": 68, "medium": 45, "low": 22}[sev]
    return min(100, max(1, base + rng.randint(-7, 7)))


def generate(now: int | None = None, seed: int = 7) -> dict[str, list[dict]]:
    now = now or int(time.time())
    rng = random.Random(seed)
    out: dict[str, list[dict]] = {}
    iid = 1000
    for product, cfg in _PRODUCTS.items():
        issues: list[dict] = []
        n = int(rng.randint(34, 60) * cfg["vol"])
        for _ in range(n):
            itype = rng.choices(list(_RULES), weights=[5, 4, 1.2, 2.5, 1.5, 1.5])[0]
            rule, cwes = rng.choice(_RULES[itype])
            sev = rng.choices(_SEV, weights=_SEV_W)[0]
            iid += 1
            detected = now - rng.randint(2, 200) * DAY
            sla_days = _SLA_DAYS[sev]
            sla_by = detected + sla_days * DAY
            # ~55% resolved; resolution time correlates with severity (criticals faster)
            closed = None
            status = "open"
            if rng.random() < 0.55:
                fix_days = max(1, int(rng.gauss({"critical": 6, "high": 16,
                              "medium": 34, "low": 70}[sev], 8)))
                ct = detected + fix_days * DAY
                if ct <= now:
                    closed, status = ct, "closed"
            elif rng.random() < 0.08:
                status = rng.choice(["ignored", "snoozed"])
            issue = {
                "id": iid, "group_id": iid, "type": itype, "rule": rule,
                "rule_id": f"aik_{itype}_{iid % 900:03d}",
                "attack_surface": rng.choice(["backend", "frontend", "cloud", "docker_container"]),
                "severity": sev, "severity_score": _score(sev, rng),
                "original_cvss_severity_score": _score(sev, rng), "status": status,
                "first_detected_at": detected, "closed_at": closed,
                "sla_days": sla_days, "sla_remediate_by": sla_by,
                "ignored_at": now if status == "ignored" else None,
                "ignored_by": "user" if status == "ignored" else None,
                "snooze_until": now + 30 * DAY if status == "snoozed" else None,
                "code_repo_name": rng.choice(cfg["repos"]),
                "code_repo_id": rng.randint(1, 99),
                "cwe_classes": cwes,
                "programming_language": cfg["lang"],
                "affected_package": rng.choice(_PKGS) if itype == "open_source" else None,
                "cve_id": rng.choice(_CVES) if itype == "open_source" else None,
                "container_repo_name": None, "cloud_name": None, "domain_name": None,
            }
            issues.append(issue)
        out[product] = issues
    return out
