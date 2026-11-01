"""CloudShift reporting service (Wave 2)."""

from __future__ import annotations

from datetime import date
from typing import Any

from cloudshift.config import CloudShiftConfig
from cloudshift.errors import CloudShiftError, CloudShiftErrorCode
from cloudshift.services.metrics_service import (
    AnnotatedIssue,
    annotate_issues,
    compute_metrics,
    issue_brief,
    priority_distribution,
)
from cloudshift.services.plane_fetch import PlaneCEClient
from cloudshift.utils.dates import parse_date, today_in_tz
from cloudshift.utils.normalization import display_name
from cloudshift.utils.resolvers import resolve_cycle, resolve_member, resolve_module, resolve_project
from cloudshift.utils.states import NormalizedState, is_terminal


def _parse_optional_date(value: str | None, tz_name: str) -> date:
    if not value:
        return today_in_tz(tz_name)
    parsed = parse_date(value)
    if not parsed:
        raise CloudShiftError(CloudShiftErrorCode.VALIDATION_FAILED, f"Invalid date: {value}")
    return parsed


class ReportingService:
    def __init__(self, client: PlaneCEClient | None = None, config: CloudShiftConfig | None = None) -> None:
        self.config = config or CloudShiftConfig.from_env()
        self.client = client or PlaneCEClient(config=self.config)
        self._owns = client is None

    def close(self) -> None:
        if self._owns:
            self.client.close()

    def __enter__(self) -> ReportingService:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _load_project_bundle(self, project: dict[str, Any]) -> dict[str, Any]:
        pid = str(project["id"])
        states = self.client.list_states(pid)
        labels = self.client.list_labels(pid)
        modules = self.client.list_modules(pid)
        cycles = self.client.list_cycles(pid)
        members = self.client.list_project_members(pid)
        issues = self.client.list_issues(pid)
        module_map = self.client.module_issue_map(pid)
        cycle_map = self.client.cycle_issue_map(pid)
        annotated = annotate_issues(
            issues,
            states=states,
            labels=labels,
            config=self.config,
            module_map=module_map,
            cycle_map=cycle_map,
            project_identifier=project.get("identifier"),
            as_of=today_in_tz(self.config.timezone),
        )
        return {
            "project": project,
            "states": states,
            "labels": labels,
            "modules": modules,
            "cycles": cycles,
            "members": members,
            "issues": issues,
            "annotated": annotated,
            "module_map": module_map,
            "cycle_map": cycle_map,
        }

    def _resolve_projects(self, project: str | None) -> list[dict[str, Any]]:
        projects = [p for p in self.client.list_projects() if not p.get("archived_at")]
        if not project:
            return projects
        hit = resolve_project(project, projects)
        return [hit.raw]

    def _filter_member(self, annotated: list[AnnotatedIssue], member_id: str | None) -> list[AnnotatedIssue]:
        if not member_id:
            return annotated
        return [a for a in annotated if member_id in a.assignee_ids]

    def daily_report(
        self,
        *,
        project: str | None = None,
        member: str | None = None,
        date_str: str | None = None,
        include_modules: bool = True,
        include_members: bool = True,
        include_blockers: bool = True,
        include_overdue: bool = True,
    ) -> dict[str, Any]:
        day = _parse_optional_date(date_str, self.config.timezone)
        projects = self._resolve_projects(project)
        member_id = None
        member_info = None
        if member:
            # resolve against union of members across selected projects
            pool: dict[str, dict[str, Any]] = {}
            for p in projects:
                for m in self.client.list_project_members(str(p["id"])):
                    pool[str(m["id"])] = m
            hit = resolve_member(member, list(pool.values()))
            member_id = hit.id
            member_info = {"id": hit.id, "name": hit.label}

        active_projects = []
        team: dict[str, dict[str, Any]] = {}
        blockers: list[dict[str, Any]] = []
        overdue_items: list[dict[str, Any]] = []
        recent_completions: list[dict[str, Any]] = []

        for p in projects:
            bundle = self._load_project_bundle(p)
            # re-annotate for specific day
            annotated = annotate_issues(
                bundle["issues"],
                states=bundle["states"],
                labels=bundle["labels"],
                config=self.config,
                as_of=day,
                module_map=bundle["module_map"],
                cycle_map=bundle["cycle_map"],
                project_identifier=p.get("identifier"),
            )
            annotated = self._filter_member(annotated, member_id)
            metrics = compute_metrics(annotated)
            completed_today = [a for a in annotated if a.completed_today]
            project_blockers = [a for a in annotated if a.blocked and not is_terminal(a.normalized_state)]
            project_overdue = [a for a in annotated if a.overdue]

            proj_entry: dict[str, Any] = {
                "project": {"id": p["id"], "name": p.get("name"), "identifier": p.get("identifier")},
                "progress": metrics.to_dict(),
                "completed_today": len(completed_today),
                "in_progress": metrics.in_progress,
                "todo": metrics.todo,
                "blocked": metrics.blocked,
                "overdue": metrics.overdue,
                "unassigned": metrics.unassigned,
            }
            if include_modules:
                module_rows = []
                for mod in bundle["modules"]:
                    mid = str(mod["id"])
                    subset = [a for a in annotated if mid in a.module_ids]
                    module_rows.append(
                        {
                            "module": {"id": mid, "name": mod.get("name")},
                            "metrics": compute_metrics(subset).to_dict(),
                        }
                    )
                proj_entry["modules"] = module_rows
            active_projects.append(proj_entry)

            if include_members:
                for m in bundle["members"]:
                    mid = str(m["id"])
                    if member_id and mid != member_id:
                        continue
                    subset = [a for a in annotated if mid in a.assignee_ids]
                    if mid not in team:
                        team[mid] = {
                            "member": {"id": mid, "name": display_name(m), "email": m.get("email")},
                            "completed_today": 0,
                            "in_progress": 0,
                            "todo": 0,
                            "blocked": 0,
                            "overdue": 0,
                        }
                    mm = compute_metrics(subset)
                    team[mid]["completed_today"] += sum(1 for a in subset if a.completed_today)
                    team[mid]["in_progress"] += mm.in_progress
                    team[mid]["todo"] += mm.todo
                    team[mid]["blocked"] += mm.blocked
                    team[mid]["overdue"] += mm.overdue

            if include_blockers:
                for a in project_blockers:
                    blockers.append({**issue_brief(a), "project": p.get("name")})
            if include_overdue:
                for a in project_overdue:
                    overdue_items.append({**issue_brief(a), "project": p.get("name")})
            for a in completed_today:
                recent_completions.append({**issue_brief(a), "project": p.get("name")})

        return {
            "report_type": "daily",
            "date": day.isoformat(),
            "timezone": self.config.timezone,
            "filter": {"project": project, "member": member_info},
            "active_projects": active_projects,
            "team": list(team.values()),
            "blockers": blockers,
            "overdue": overdue_items,
            "recent_completions": recent_completions,
        }

    def user_report(self, member: str, *, project: str | None = None) -> dict[str, Any]:
        projects = self._resolve_projects(project)
        pool: dict[str, dict[str, Any]] = {}
        for p in projects:
            for m in self.client.list_project_members(str(p["id"])):
                pool[str(m["id"])] = m
        hit = resolve_member(member, list(pool.values()))
        mid = hit.id

        all_annotated: list[AnnotatedIssue] = []
        project_rows = []
        module_rows = []
        cycle_names: set[str] = set()

        for p in projects:
            bundle = self._load_project_bundle(p)
            annotated = [a for a in bundle["annotated"] if mid in a.assignee_ids]
            if not annotated and str(p["id"]) not in {str(x.get("project")) for x in []}:
                # still include project if member belongs
                member_ids = {str(m["id"]) for m in bundle["members"]}
                if mid not in member_ids:
                    continue
            all_annotated.extend(annotated)
            project_rows.append(
                {
                    "project": {"id": p["id"], "name": p.get("name"), "identifier": p.get("identifier")},
                    "metrics": compute_metrics(annotated).to_dict(),
                }
            )
            for mod in bundle["modules"]:
                subset = [a for a in annotated if str(mod["id"]) in a.module_ids]
                if not subset:
                    continue
                mm = compute_metrics(subset)
                module_rows.append(
                    {
                        "project": p.get("name"),
                        "module": {"id": mod["id"], "name": mod.get("name")},
                        "assigned": mm.total,
                        "completed": mm.completed,
                        "active": mm.todo + mm.in_progress + mm.backlog,
                        "blocked": mm.blocked,
                        "progress_percent": mm.completion_percentage,
                    }
                )
            for cy in bundle["cycles"]:
                if any(str(cy["id"]) in a.cycle_ids for a in annotated):
                    cycle_names.add(cy.get("name") or str(cy["id"]))

        metrics = compute_metrics(all_annotated)
        focus = [issue_brief(a) for a in all_annotated if a.normalized_state == NormalizedState.IN_PROGRESS]
        high_priority = [
            issue_brief(a)
            for a in all_annotated
            if str(a.raw.get("priority") or "").lower() in {"urgent", "high"} and not is_terminal(a.normalized_state)
        ]
        blocked = [issue_brief(a) for a in all_annotated if a.blocked and not is_terminal(a.normalized_state)]
        recently_completed = [issue_brief(a) for a in all_annotated if a.normalized_state == NormalizedState.COMPLETED][
            :20
        ]

        return {
            "report_type": "user",
            "member": {"id": mid, "name": hit.label, "email": hit.raw.get("email")},
            "projects": project_rows,
            "modules": module_rows,
            "cycles": sorted(cycle_names),
            "metrics": metrics.to_dict(),
            "current_focus": focus,
            "recently_completed": recently_completed,
            "high_priority_work": high_priority,
            "blocked": blocked,
        }

    def module_report(self, module: str, *, project: str | None = None) -> dict[str, Any]:
        projects = self._resolve_projects(project)
        # find module across projects
        found = None
        bundle = None
        for p in projects:
            b = self._load_project_bundle(p)
            try:
                hit = resolve_module(module, b["modules"])
                found = (p, hit)
                bundle = b
                break
            except CloudShiftError as exc:
                if exc.code == CloudShiftErrorCode.MODULE_AMBIGUOUS:
                    raise
                continue
        if not found or bundle is None:
            raise CloudShiftError(CloudShiftErrorCode.MODULE_NOT_FOUND, f"Module not found: {module}")

        project, hit = found
        mid = hit.id
        annotated = [a for a in bundle["annotated"] if mid in a.module_ids]
        metrics = compute_metrics(annotated)
        members = []
        for m in bundle["members"]:
            uid = str(m["id"])
            subset = [a for a in annotated if uid in a.assignee_ids]
            if not subset:
                continue
            mm = compute_metrics(subset)
            members.append(
                {
                    "member": {"id": uid, "name": display_name(m)},
                    "assigned": mm.total,
                    "completed": mm.completed,
                    "active": mm.todo + mm.in_progress + mm.backlog,
                    "blocked": mm.blocked,
                    "overdue": mm.overdue,
                }
            )
        return {
            "report_type": "module",
            "module": {"id": mid, "name": hit.label},
            "project": {
                "id": project["id"],
                "name": project.get("name"),
                "identifier": project.get("identifier"),
            },
            "metrics": metrics.to_dict(),
            "members_involved": members,
            "items": [issue_brief(a) for a in annotated],
        }

    def project_report(self, project: str) -> dict[str, Any]:
        projects = self._resolve_projects(project)
        p = projects[0]
        bundle = self._load_project_bundle(p)
        annotated = bundle["annotated"]
        metrics = compute_metrics(annotated)
        state_dist = {
            "BACKLOG": metrics.backlog,
            "TODO": metrics.todo,
            "IN_PROGRESS": metrics.in_progress,
            "COMPLETED": metrics.completed,
            "CANCELLED": metrics.cancelled,
        }
        module_progress = []
        for mod in bundle["modules"]:
            subset = [a for a in annotated if str(mod["id"]) in a.module_ids]
            module_progress.append(
                {"module": {"id": mod["id"], "name": mod.get("name")}, "metrics": compute_metrics(subset).to_dict()}
            )
        cycle_progress = []
        for cy in bundle["cycles"]:
            subset = [a for a in annotated if str(cy["id"]) in a.cycle_ids]
            cycle_progress.append(
                {
                    "cycle": {
                        "id": cy["id"],
                        "name": cy.get("name"),
                        "start_date": cy.get("start_date"),
                        "end_date": cy.get("end_date"),
                    },
                    "metrics": compute_metrics(subset).to_dict(),
                }
            )
        member_workload = []
        for m in bundle["members"]:
            uid = str(m["id"])
            subset = [a for a in annotated if uid in a.assignee_ids]
            member_workload.append(
                {
                    "member": {"id": uid, "name": display_name(m)},
                    "metrics": compute_metrics(subset).to_dict(),
                }
            )
        return {
            "report_type": "project",
            "project": {
                "id": p["id"],
                "name": p.get("name"),
                "identifier": p.get("identifier"),
                "description": p.get("description"),
            },
            "overall_progress": metrics.to_dict(),
            "state_distribution": state_dist,
            "priority_distribution": priority_distribution(annotated),
            "module_progress": module_progress,
            "cycle_progress": cycle_progress,
            "member_workload": member_workload,
            "blocked_work": [issue_brief(a) for a in annotated if a.blocked and not is_terminal(a.normalized_state)],
            "overdue_work": [issue_brief(a) for a in annotated if a.overdue],
            "stale_work": [issue_brief(a) for a in annotated if a.stale],
            "unassigned_work": [
                issue_brief(a) for a in annotated if a.unassigned and not is_terminal(a.normalized_state)
            ],
            "recent_completions": [
                issue_brief(a) for a in annotated if a.normalized_state == NormalizedState.COMPLETED
            ][:25],
            "high_priority_unfinished": [
                issue_brief(a)
                for a in annotated
                if str(a.raw.get("priority") or "").lower() in {"urgent", "high"}
                and not is_terminal(a.normalized_state)
            ],
        }

    def cycle_report(self, cycle: str, *, project: str | None = None) -> dict[str, Any]:
        projects = self._resolve_projects(project)
        found = None
        bundle = None
        for p in projects:
            b = self._load_project_bundle(p)
            try:
                hit = resolve_cycle(cycle, b["cycles"])
                found = (p, hit)
                bundle = b
                break
            except CloudShiftError as exc:
                if exc.code == CloudShiftErrorCode.CYCLE_AMBIGUOUS:
                    raise
                continue
        if not found or bundle is None:
            raise CloudShiftError(CloudShiftErrorCode.CYCLE_NOT_FOUND, f"Cycle not found: {cycle}")
        project, hit = found
        cid = hit.id
        annotated = [a for a in bundle["annotated"] if cid in a.cycle_ids]
        metrics = compute_metrics(annotated)
        unfinished = [issue_brief(a) for a in annotated if not is_terminal(a.normalized_state)]
        module_dist = []
        for mod in bundle["modules"]:
            subset = [a for a in annotated if str(mod["id"]) in a.module_ids]
            if subset:
                module_dist.append(
                    {"module": {"id": mod["id"], "name": mod.get("name")}, "metrics": compute_metrics(subset).to_dict()}
                )
        member_dist = []
        for m in bundle["members"]:
            uid = str(m["id"])
            subset = [a for a in annotated if uid in a.assignee_ids]
            if subset:
                member_dist.append(
                    {"member": {"id": uid, "name": display_name(m)}, "metrics": compute_metrics(subset).to_dict()}
                )
        return {
            "report_type": "cycle",
            "cycle": {
                "id": cid,
                "name": hit.label,
                "start_date": hit.raw.get("start_date"),
                "end_date": hit.raw.get("end_date"),
            },
            "project": {
                "id": project["id"],
                "name": project.get("name"),
                "identifier": project.get("identifier"),
            },
            "metrics": {
                **metrics.to_dict(),
                "total_committed": metrics.total,
                "completion_percent": metrics.completion_percentage,
            },
            "module_distribution": module_dist,
            "member_distribution": member_dist,
            "unfinished_items": unfinished,
            "carry_forward_candidates": unfinished,
            "scope_added_after_start": None,
            "warnings": [
                "scope_added_after_start omitted: historical scope-change activity not reliably available on CE 0.23.1"
            ],
        }

    def workspace_report(self) -> dict[str, Any]:
        projects = self._resolve_projects(None)
        portfolio = []
        team: dict[str, dict[str, Any]] = {}
        critical_blockers = []
        overdue_items = []
        at_risk_projects = []
        at_risk_modules = []
        current_cycles = []
        recent_delivery = []

        for p in projects:
            bundle = self._load_project_bundle(p)
            annotated = bundle["annotated"]
            metrics = compute_metrics(annotated)
            health = "HEALTHY"
            reasons = []
            if metrics.overdue_percentage >= 15:
                health = "AT_RISK"
                reasons.append(f"{metrics.overdue_percentage}% overdue")
            if metrics.blocked_percentage >= 10:
                health = "AT_RISK" if health == "HEALTHY" else health
                reasons.append(f"{metrics.blocked_percentage}% blocked")
            if metrics.completion_percentage < 30 and metrics.total >= 5:
                if health == "HEALTHY":
                    health = "WATCH"
                reasons.append(f"completion {metrics.completion_percentage}%")

            portfolio.append(
                {
                    "project": {"id": p["id"], "name": p.get("name"), "identifier": p.get("identifier")},
                    "progress": metrics.to_dict(),
                    "health": health,
                    "active": metrics.todo + metrics.in_progress + metrics.backlog,
                    "completed": metrics.completed,
                    "blocked": metrics.blocked,
                    "overdue": metrics.overdue,
                    "reasons": reasons,
                }
            )
            if health in {"AT_RISK", "CRITICAL"}:
                at_risk_projects.append(portfolio[-1])

            for mod in bundle["modules"]:
                subset = [a for a in annotated if str(mod["id"]) in a.module_ids]
                mm = compute_metrics(subset)
                if mm.total and (
                    mm.overdue_percentage >= 20 or mm.blocked_percentage >= 15 or mm.completion_percentage < 40
                ):
                    at_risk_modules.append(
                        {
                            "project": p.get("name"),
                            "module": {"id": mod["id"], "name": mod.get("name")},
                            "metrics": mm.to_dict(),
                        }
                    )

            for cy in bundle["cycles"]:
                if cy.get("archived_at"):
                    continue
                current_cycles.append(
                    {
                        "project": p.get("name"),
                        "cycle": {
                            "id": cy["id"],
                            "name": cy.get("name"),
                            "start_date": cy.get("start_date"),
                            "end_date": cy.get("end_date"),
                        },
                    }
                )

            for m in bundle["members"]:
                uid = str(m["id"])
                subset = [a for a in annotated if uid in a.assignee_ids]
                mm = compute_metrics(subset)
                if uid not in team:
                    team[uid] = {
                        "member": {"id": uid, "name": display_name(m), "email": m.get("email")},
                        "active_workload": 0,
                        "completed": 0,
                        "blocked": 0,
                        "overdue": 0,
                    }
                team[uid]["active_workload"] += mm.todo + mm.in_progress + mm.backlog
                team[uid]["completed"] += mm.completed
                team[uid]["blocked"] += mm.blocked
                team[uid]["overdue"] += mm.overdue

            for a in annotated:
                if a.blocked and not is_terminal(a.normalized_state):
                    critical_blockers.append({**issue_brief(a), "project": p.get("name")})
                if a.overdue:
                    overdue_items.append({**issue_brief(a), "project": p.get("name")})
                if a.completed_today:
                    recent_delivery.append({**issue_brief(a), "project": p.get("name")})

        return {
            "report_type": "workspace",
            "timezone": self.config.timezone,
            "project_portfolio": portfolio,
            "team": list(team.values()),
            "critical_blockers": critical_blockers,
            "overdue_items": overdue_items,
            "at_risk_projects": at_risk_projects,
            "at_risk_modules": at_risk_modules,
            "current_cycles": current_cycles,
            "recent_delivery": recent_delivery,
            "warnings": [
                "Health labels in workspace_report are deterministic heuristics for Wave 2; "
                "full configurable health engine arrives in Wave 3."
            ],
        }
