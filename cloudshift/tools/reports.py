"""CloudShift reporting MCP tools."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from cloudshift.errors import CloudShiftError, ok
from cloudshift.services.reporting_service import ReportingService


def _run(fn) -> dict[str, Any]:
    try:
        with ReportingService() as svc:
            data = fn(svc)
        return ok(data, metadata={"wave": 2, "plane_edition": "ce-0.23.1-adapter"})
    except CloudShiftError as exc:
        return exc.to_dict()


def register_report_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def cloudshift_plane_daily_report(
        project: str | None = None,
        member: str | None = None,
        date: str | None = None,
        include_modules: bool = True,
        include_members: bool = True,
        include_blockers: bool = True,
        include_overdue: bool = True,
    ) -> dict[str, Any]:
        """Daily CloudShift status report (CE-compatible, deterministic metrics).

        Omit project for workspace-level rollup. Member/project accept name, identifier, or UUID.
        Date is YYYY-MM-DD in CLOUDSHIFT_TIMEZONE (default UTC).
        """
        return _run(
            lambda svc: svc.daily_report(
                project=project,
                member=member,
                date_str=date,
                include_modules=include_modules,
                include_members=include_members,
                include_blockers=include_blockers,
                include_overdue=include_overdue,
            )
        )

    @mcp.tool()
    def cloudshift_plane_user_report(member: str, project: str | None = None) -> dict[str, Any]:
        """User workload/status report across projects/modules (READ-only)."""
        return _run(lambda svc: svc.user_report(member, project=project))

    @mcp.tool()
    def cloudshift_plane_module_report(module: str, project: str | None = None) -> dict[str, Any]:
        """Module report with per-member breakdown (READ-only)."""
        return _run(lambda svc: svc.module_report(module, project=project))

    @mcp.tool()
    def cloudshift_plane_project_report(project: str) -> dict[str, Any]:
        """Full project report: progress, distributions, blockers, overdue, stale (READ-only)."""
        return _run(lambda svc: svc.project_report(project))

    @mcp.tool()
    def cloudshift_plane_cycle_report(cycle: str, project: str | None = None) -> dict[str, Any]:
        """Cycle/sprint report with unfinished and carry-forward candidates (READ-only)."""
        return _run(lambda svc: svc.cycle_report(cycle, project=project))

    @mcp.tool()
    def cloudshift_plane_workspace_report() -> dict[str, Any]:
        """Workspace portfolio report across all active projects (READ-only)."""
        return _run(lambda svc: svc.workspace_report())
