"""CloudShift configuration (additive to upstream PLANE_* vars)."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class CloudShiftConfig:
    timezone: str = "UTC"
    stale_task_days: int = 5
    due_soon_hours: int = 48
    max_bulk_operation_size: int = 50
    http_timeout_seconds: float = 45.0
    blocked_label_names: tuple[str, ...] = ("blocked", "blocker", "blocking")

    @classmethod
    def from_env(cls) -> CloudShiftConfig:
        blocked = os.getenv("CLOUDSHIFT_BLOCKED_LABEL_NAMES", "blocked,blocker,blocking")
        names = tuple(n.strip().lower() for n in blocked.split(",") if n.strip())
        return cls(
            timezone=os.getenv("CLOUDSHIFT_TIMEZONE", "UTC"),
            stale_task_days=_int_env("CLOUDSHIFT_STALE_TASK_DAYS", 5),
            due_soon_hours=_int_env("CLOUDSHIFT_DUE_SOON_HOURS", 48),
            max_bulk_operation_size=_int_env("CLOUDSHIFT_MAX_BULK_OPERATION_SIZE", 50),
            blocked_label_names=names or ("blocked", "blocker", "blocking"),
        )


def plane_base_url() -> str:
    return (os.getenv("PLANE_INTERNAL_BASE_URL") or os.getenv("PLANE_BASE_URL") or "").rstrip("/")


def plane_api_key() -> str:
    return os.getenv("PLANE_API_KEY", "")


def plane_workspace_slug() -> str:
    return os.getenv("PLANE_WORKSPACE_SLUG", "")
