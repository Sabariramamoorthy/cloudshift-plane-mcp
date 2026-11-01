"""CloudShift diagnostic MCP tools."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from cloudshift.config import CloudShiftConfig, plane_base_url, plane_workspace_slug
from cloudshift.errors import CloudShiftError, ok
from cloudshift.services.plane_fetch import PlaneCEClient


def register_diagnostic_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def cloudshift_plane_capability_report() -> dict[str, Any]:
        """READ-only CE capability snapshot for CloudShift (no mutations)."""
        cfg = CloudShiftConfig.from_env()
        try:
            with PlaneCEClient(config=cfg) as client:
                projects = client.list_projects()
                sample = next((p for p in projects if not p.get("archived_at")), None)
                detail: dict[str, Any] = {}
                if sample:
                    pid = str(sample["id"])
                    detail = {
                        "sample_project": {
                            "id": pid,
                            "name": sample.get("name"),
                            "identifier": sample.get("identifier"),
                        },
                        "states": len(client.list_states(pid)),
                        "labels": len(client.list_labels(pid)),
                        "modules": len(client.list_modules(pid)),
                        "cycles": len(client.list_cycles(pid)),
                        "members": len(client.list_project_members(pid)),
                        "issues": len(client.list_issues(pid)),
                    }
                data = {
                    "plane_base_url": plane_base_url(),
                    "workspace_slug": plane_workspace_slug(),
                    "timezone": cfg.timezone,
                    "project_count": len(projects),
                    "adapter": "ce-0.23.1-issues",
                    "sample": detail,
                    "notes": [
                        "Upstream MCP work-item tools may 404 on this CE build; use cloudshift_plane_* reports.",
                        "Work items are fetched via /issues/ paths.",
                    ],
                }
                return ok(data, metadata={"wave": 2})
        except CloudShiftError as exc:
            return exc.to_dict()
