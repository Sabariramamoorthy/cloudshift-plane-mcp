"""Shared report model helpers (Wave 2)."""

from __future__ import annotations

from typing import Any, TypedDict


class ToolEnvelope(TypedDict, total=False):
    success: bool
    data: Any
    warnings: list[str]
    metadata: dict[str, Any]
    error: dict[str, Any]
