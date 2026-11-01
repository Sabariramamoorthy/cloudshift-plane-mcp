"""State group normalization for Plane CE."""

from __future__ import annotations

from enum import Enum
from typing import Any


class NormalizedState(str, Enum):
    BACKLOG = "BACKLOG"
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


# Plane CE uses group values: backlog, unstarted, started, completed, cancelled
_GROUP_MAP = {
    "backlog": NormalizedState.BACKLOG,
    "unstarted": NormalizedState.TODO,
    "todo": NormalizedState.TODO,
    "started": NormalizedState.IN_PROGRESS,
    "in_progress": NormalizedState.IN_PROGRESS,
    "in-progress": NormalizedState.IN_PROGRESS,
    "completed": NormalizedState.COMPLETED,
    "done": NormalizedState.COMPLETED,
    "cancelled": NormalizedState.CANCELLED,
    "canceled": NormalizedState.CANCELLED,
}


def classify_state_group(group: str | None) -> NormalizedState:
    if not group:
        return NormalizedState.UNKNOWN
    return _GROUP_MAP.get(str(group).strip().lower(), NormalizedState.UNKNOWN)


def state_lookup(states: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(s["id"]): s for s in states if s.get("id")}


def classify_issue_state(issue: dict[str, Any], states_by_id: dict[str, dict[str, Any]]) -> NormalizedState:
    state_field = issue.get("state")
    if isinstance(state_field, dict):
        group = state_field.get("group")
        if group:
            return classify_state_group(group)
        state_id = state_field.get("id")
    else:
        state_id = state_field
    if state_id and str(state_id) in states_by_id:
        return classify_state_group(states_by_id[str(state_id)].get("group"))
    return NormalizedState.UNKNOWN


def is_terminal(norm: NormalizedState) -> bool:
    return norm in {NormalizedState.COMPLETED, NormalizedState.CANCELLED}
