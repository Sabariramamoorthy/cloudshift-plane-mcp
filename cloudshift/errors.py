"""Normalized CloudShift error codes (no secrets / no stack traces)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class CloudShiftErrorCode:
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    PROJECT_AMBIGUOUS = "PROJECT_AMBIGUOUS"
    MEMBER_NOT_FOUND = "MEMBER_NOT_FOUND"
    MEMBER_AMBIGUOUS = "MEMBER_AMBIGUOUS"
    MODULE_NOT_FOUND = "MODULE_NOT_FOUND"
    MODULE_AMBIGUOUS = "MODULE_AMBIGUOUS"
    CYCLE_NOT_FOUND = "CYCLE_NOT_FOUND"
    CYCLE_AMBIGUOUS = "CYCLE_AMBIGUOUS"
    WORK_ITEM_NOT_FOUND = "WORK_ITEM_NOT_FOUND"
    WORK_ITEM_AMBIGUOUS = "WORK_ITEM_AMBIGUOUS"
    PLANE_AUTH_FAILED = "PLANE_AUTH_FAILED"
    PLANE_UNAVAILABLE = "PLANE_UNAVAILABLE"
    CAPABILITY_UNSUPPORTED = "CAPABILITY_UNSUPPORTED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"


@dataclass
class CloudShiftError(Exception):
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            },
            "warnings": [],
            "metadata": {},
        }


def ok(data: Any, *, warnings: list[str] | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "success": True,
        "data": data,
        "warnings": warnings or [],
        "metadata": metadata or {},
    }
