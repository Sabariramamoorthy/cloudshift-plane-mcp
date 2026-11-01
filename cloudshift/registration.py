"""Register CloudShift MCP tools with FastMCP."""

from __future__ import annotations

from fastmcp import FastMCP

from cloudshift.tools.diagnostics import register_diagnostic_tools
from cloudshift.tools.reports import register_report_tools


def register_cloudshift_tools(mcp: FastMCP) -> None:
    """Register all CloudShift extension tools (Wave 2+)."""
    register_diagnostic_tools(mcp)
    register_report_tools(mcp)
