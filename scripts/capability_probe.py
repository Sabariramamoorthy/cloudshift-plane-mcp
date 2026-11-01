#!/usr/bin/env python3
"""Read-only probe of which Plane API endpoints your instance serves.

Never creates, updates, or deletes Plane data. Reads PLANE_BASE_URL, PLANE_API_KEY,
and PLANE_WORKSPACE_SLUG from the environment, then .env.local, then .env.

Usage:
  uv run --extra dev python scripts/capability_probe.py
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class ProbeResult:
    name: str
    method: str
    url: str
    status: int | None
    ok: bool
    notes: str


def load_config() -> dict[str, str]:
    file_cfg: dict[str, str] = {}
    for env_path in (ROOT / ".env", ROOT / ".env.local"):
        if env_path.exists():
            file_cfg.update({k: v for k, v in dotenv_values(env_path).items() if v})
    base = os.getenv("PLANE_BASE_URL") or file_cfg.get("PLANE_BASE_URL", "")
    key = os.getenv("PLANE_API_KEY") or file_cfg.get("PLANE_API_KEY", "")
    slug = os.getenv("PLANE_WORKSPACE_SLUG") or file_cfg.get("PLANE_WORKSPACE_SLUG", "")
    if not base or not key or not slug:
        raise SystemExit("Missing PLANE_BASE_URL / PLANE_API_KEY / PLANE_WORKSPACE_SLUG")
    return {"base": base.rstrip("/"), "key": key, "slug": slug}


def probe(client: httpx.Client, name: str, method: str, url: str, headers: dict[str, str]) -> ProbeResult:
    try:
        response = client.request(method, url, headers=headers)
        body = response.text[:240].replace("\n", " ")
        ok = 200 <= response.status_code < 300
        notes = body
        if response.status_code == 401:
            notes = f"unauthorized: {body}"
        elif response.status_code == 403:
            notes = f"forbidden: {body}"
        elif response.status_code == 404:
            notes = f"not_found: {body}"
        return ProbeResult(name, method, url, response.status_code, ok, notes)
    except httpx.HTTPError as exc:
        return ProbeResult(name, method, url, None, False, f"{type(exc).__name__}: {exc}")


def main() -> int:
    cfg = load_config()
    base = cfg["base"]
    key = cfg["key"]
    slug = cfg["slug"]
    auth_headers = {
        "X-Api-Key": key,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    results: list[ProbeResult] = []
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        # Public instance metadata (no auth required on Plane CE)
        results.append(probe(client, "instance_metadata", "GET", f"{base}/api/instances/", {}))

        # Path / auth discovery — READ only
        for name, path in [
            ("users_me_api_v1", "/api/v1/users/me/"),
            ("users_me_api", "/api/users/me/"),
            ("workspaces_api_v1", f"/api/v1/workspaces/{slug}/"),
            ("workspaces_api", f"/api/workspaces/{slug}/"),
            ("projects_api_v1", f"/api/v1/workspaces/{slug}/projects/"),
            ("projects_api", f"/api/workspaces/{slug}/projects/"),
            ("members_api", f"/api/workspaces/{slug}/members/"),
            ("api_tokens_list", f"/api/workspaces/{slug}/api-tokens/"),
        ]:
            results.append(probe(client, name, "GET", f"{base}{path}", auth_headers))

        # SDK-shaped call (documents plane-sdk incompatibility if /api/v1 missing)
        try:
            from plane import PlaneClient

            client_sdk = PlaneClient(base_url=base, api_key=key)
            # users resource methods vary by sdk version; attempt common patterns
            me = None
            err = None
            try:
                if hasattr(client_sdk.users, "retrieve_current"):
                    me = client_sdk.users.retrieve_current()
                elif hasattr(client_sdk.users, "current"):
                    me = client_sdk.users.current()
                elif hasattr(client_sdk.users, "me"):
                    me = client_sdk.users.me()
                else:
                    # fall back to projects list as auth+path smoke
                    me = client_sdk.projects.list(workspace_slug=slug)
            except Exception as exc:  # noqa: BLE001 - probe must never crash
                err = f"{type(exc).__name__}: {exc}"
            results.append(
                ProbeResult(
                    name="plane_sdk_smoke",
                    method="SDK",
                    url=f"{base}/api/v1/... (sdk appends /api/v1)",
                    status=200 if me is not None and err is None else None,
                    ok=me is not None and err is None,
                    notes=("ok" if err is None else err)[:400],
                )
            )
        except Exception as exc:  # noqa: BLE001
            results.append(ProbeResult("plane_sdk_import", "SDK", "plane.PlaneClient", None, False, str(exc)[:400]))

    payload = {
        "success": True,
        "config": {
            "base_url": base,
            "workspace_slug": slug,
            "api_key_prefix": key[:12],
            "api_key_length": len(key),
        },
        "results": [asdict(r) for r in results],
        "summary": {
            "ok": sum(1 for r in results if r.ok),
            "failed": sum(1 for r in results if not r.ok),
            "total": len(results),
        },
    }
    print(json.dumps(payload, indent=2))
    # Non-zero if authenticated API paths failed (expected until instance is API-ready)
    return 0 if any(r.ok and r.name.startswith("users_me") for r in results) else 2


if __name__ == "__main__":
    sys.exit(main())
