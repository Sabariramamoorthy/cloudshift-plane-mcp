"""Deterministic metrics — never LLM-calculated."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from cloudshift.config import CloudShiftConfig
from cloudshift.utils.dates import parse_date, parse_datetime, safe_pct, today_in_tz
from cloudshift.utils.normalization import display_name, issue_key
from cloudshift.utils.states import (
    NormalizedState,
    classify_issue_state,
    is_terminal,
    state_lookup,
)


@dataclass
class MetricBucket:
    total: int = 0
    backlog: int = 0
    todo: int = 0
    in_progress: int = 0
    completed: int = 0
    cancelled: int = 0
    blocked: int = 0
    overdue: int = 0
    due_soon: int = 0
    unassigned: int = 0
    stale: int = 0
    completion_percentage: float = 0.0
    active_percentage: float = 0.0
    blocked_percentage: float = 0.0
    overdue_percentage: float = 0.0

    def finalize(self) -> MetricBucket:
        self.completion_percentage = safe_pct(self.completed, self.total)
        active = self.todo + self.in_progress + self.backlog
        self.active_percentage = safe_pct(active, self.total)
        self.blocked_percentage = safe_pct(self.blocked, self.total)
        self.overdue_percentage = safe_pct(self.overdue, self.total)
        return self

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.finalize())


@dataclass
class AnnotatedIssue:
    raw: dict[str, Any]
    normalized_state: NormalizedState
    blocked: bool
    overdue: bool
    due_soon: bool
    unassigned: bool
    stale: bool
    completed_today: bool
    assignee_ids: list[str]
    label_names: list[str]
    module_ids: set[str] = field(default_factory=set)
    cycle_ids: set[str] = field(default_factory=set)
    key: str | None = None


def _assignee_ids(issue: dict[str, Any]) -> list[str]:
    assignees = issue.get("assignees") or []
    ids: list[str] = []
    for a in assignees:
        if isinstance(a, str):
            ids.append(a)
        elif isinstance(a, dict) and a.get("id"):
            ids.append(str(a["id"]))
    return ids


def _label_names(issue: dict[str, Any], labels_by_id: dict[str, dict[str, Any]]) -> list[str]:
    labels = issue.get("labels") or []
    names: list[str] = []
    for lab in labels:
        if isinstance(lab, dict):
            names.append(str(lab.get("name") or ""))
        elif isinstance(lab, str) and lab in labels_by_id:
            names.append(str(labels_by_id[lab].get("name") or ""))
    return [n for n in names if n]


def _state_name(issue: dict[str, Any], states_by_id: dict[str, dict[str, Any]]) -> str:
    state_field = issue.get("state")
    if isinstance(state_field, dict):
        return str(state_field.get("name") or "")
    if state_field and str(state_field) in states_by_id:
        return str(states_by_id[str(state_field)].get("name") or "")
    return ""


def is_blocked_issue(
    issue: dict[str, Any],
    *,
    states_by_id: dict[str, dict[str, Any]],
    labels_by_id: dict[str, dict[str, Any]],
    blocked_label_names: tuple[str, ...],
) -> bool:
    state_name = _state_name(issue, states_by_id).lower()
    if "block" in state_name:
        return True
    for name in _label_names(issue, labels_by_id):
        if name.lower() in blocked_label_names or "block" in name.lower():
            return True
    return False


def annotate_issues(
    issues: list[dict[str, Any]],
    *,
    states: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    config: CloudShiftConfig,
    as_of: date | None = None,
    now: datetime | None = None,
    module_map: dict[str, set[str]] | None = None,
    cycle_map: dict[str, set[str]] | None = None,
    project_identifier: str | None = None,
) -> list[AnnotatedIssue]:
    states_by_id = state_lookup(states)
    labels_by_id = {str(lbl["id"]): lbl for lbl in labels if lbl.get("id")}
    day = as_of or today_in_tz(config.timezone)
    from cloudshift.utils.dates import now_tz

    current = now or now_tz(config.timezone)
    stale_before = current - timedelta(days=config.stale_task_days)
    due_soon_until = current + timedelta(hours=config.due_soon_hours)
    day_start = datetime(day.year, day.month, day.day, tzinfo=current.tzinfo)

    annotated: list[AnnotatedIssue] = []
    for issue in issues:
        if issue.get("is_draft"):
            continue
        norm = classify_issue_state(issue, states_by_id)
        blocked = is_blocked_issue(
            issue,
            states_by_id=states_by_id,
            labels_by_id=labels_by_id,
            blocked_label_names=config.blocked_label_names,
        )
        assignees = _assignee_ids(issue)
        unassigned = len(assignees) == 0
        target = parse_date(issue.get("target_date"))
        overdue = bool(target and target < day and not is_terminal(norm))
        due_soon = False
        if target and not is_terminal(norm) and not overdue:
            # interpret date as end of day in workspace tz
            target_dt = datetime(target.year, target.month, target.day, 23, 59, 59, tzinfo=current.tzinfo)
            due_soon = day_start <= target_dt <= due_soon_until
        updated = parse_datetime(issue.get("updated_at"))
        stale = bool(updated and updated < stale_before and not is_terminal(norm))
        completed_at = parse_datetime(issue.get("completed_at"))
        completed_today = bool(
            norm == NormalizedState.COMPLETED and completed_at and completed_at.astimezone(current.tzinfo).date() == day
        )
        iid = str(issue.get("id"))
        annotated.append(
            AnnotatedIssue(
                raw=issue,
                normalized_state=norm,
                blocked=blocked,
                overdue=overdue,
                due_soon=due_soon,
                unassigned=unassigned,
                stale=stale,
                completed_today=completed_today,
                assignee_ids=assignees,
                label_names=_label_names(issue, labels_by_id),
                module_ids=(module_map or {}).get(iid, set()),
                cycle_ids=(cycle_map or {}).get(iid, set()),
                key=issue_key(project_identifier or issue.get("project_identifier"), issue.get("sequence_id")),
            )
        )
    return annotated


def compute_metrics(items: list[AnnotatedIssue]) -> MetricBucket:
    bucket = MetricBucket(total=len(items))
    for item in items:
        if item.normalized_state == NormalizedState.BACKLOG:
            bucket.backlog += 1
        elif item.normalized_state == NormalizedState.TODO:
            bucket.todo += 1
        elif item.normalized_state == NormalizedState.IN_PROGRESS:
            bucket.in_progress += 1
        elif item.normalized_state == NormalizedState.COMPLETED:
            bucket.completed += 1
        elif item.normalized_state == NormalizedState.CANCELLED:
            bucket.cancelled += 1
        if item.blocked and not is_terminal(item.normalized_state):
            bucket.blocked += 1
        if item.overdue:
            bucket.overdue += 1
        if item.due_soon:
            bucket.due_soon += 1
        if item.unassigned and not is_terminal(item.normalized_state):
            bucket.unassigned += 1
        if item.stale:
            bucket.stale += 1
    return bucket.finalize()


def issue_brief(item: AnnotatedIssue) -> dict[str, Any]:
    return {
        "id": item.raw.get("id"),
        "key": item.key,
        "name": item.raw.get("name"),
        "priority": item.raw.get("priority"),
        "state": item.normalized_state.value,
        "blocked": item.blocked,
        "overdue": item.overdue,
        "due_soon": item.due_soon,
        "unassigned": item.unassigned,
        "stale": item.stale,
        "target_date": item.raw.get("target_date"),
        "assignees": item.assignee_ids,
        "module_ids": sorted(item.module_ids),
        "cycle_ids": sorted(item.cycle_ids),
    }


def priority_distribution(items: list[AnnotatedIssue]) -> dict[str, int]:
    dist: dict[str, int] = {}
    for item in items:
        p = str(item.raw.get("priority") or "none")
        dist[p] = dist.get(p, 0) + 1
    return dist


def member_label(member: dict[str, Any]) -> str:
    return display_name(member)
