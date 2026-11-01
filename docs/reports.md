# Report tools

The seven `cloudshift_plane_*` tools build status reports by reading Plane and computing every number in Python. The model only formats and explains the result, so a report is reproducible: the same data gives the same counts.

All report tools are **read-only**. They read Plane through their own client in `cloudshift/services/plane_fetch.py`, which uses the `/issues/` API paths that self-hosted Community Edition supports. They work even where some upstream work-item tools return 404.

> **Credentials:** report tools always use the server's `PLANE_API_KEY` and `PLANE_WORKSPACE_SLUG`, not the key of the client that called them. Anyone who can call the server can therefore read reports for that workspace. Run one server per team or workspace; don't share an HTTP server across tenants.

## Tools

| Tool | Arguments | Use for |
|---|---|---|
| `cloudshift_plane_daily_report` | `project?`, `member?`, `date?` (YYYY-MM-DD), `include_modules`, `include_members`, `include_blockers`, `include_overdue` | Standups: per-project progress, per-person counts, blockers, overdue, completions on the day |
| `cloudshift_plane_user_report` | `member`, `project?` | One person's workload: modules, cycles, current focus, high-priority and blocked work |
| `cloudshift_plane_module_report` | `module`, `project?` | Module progress with per-member breakdown and item list |
| `cloudshift_plane_project_report` | `project` | Project health: state/priority distribution, module and cycle progress, workload, blocked/overdue/stale/unassigned |
| `cloudshift_plane_cycle_report` | `cycle`, `project?` | Sprint review: unfinished items and carry-forward candidates |
| `cloudshift_plane_workspace_report` | — | Portfolio view: project health, team, critical blockers, at-risk projects and modules |
| `cloudshift_plane_capability_report` | — | What this Plane instance supports (sample counts per resource) |

`project`, `member`, `module`, and `cycle` accept a **name, identifier, or UUID**: `"DEMO"`, `"Demo Project"`, or the project ID. Members match on full name, first name, display name, or email. When a name matches more than one entity, the tool returns an `*_AMBIGUOUS` error listing the candidates rather than guessing. Omit `project` on the daily and user reports to cover every active project.

## Response envelope

```json
{
  "success": true,
  "data": { "report_type": "daily", "...": "..." },
  "warnings": [],
  "metadata": { "wave": 2, "plane_edition": "ce-0.23.1-adapter" }
}
```

On failure, `success` is `false` and `error` holds `code`, `message`, and `details`. Errors never include stack traces or credentials.

| Error code | Meaning |
|---|---|
| `PROJECT_NOT_FOUND` / `PROJECT_AMBIGUOUS` | Project argument matched nothing / several projects |
| `MEMBER_NOT_FOUND` / `MEMBER_AMBIGUOUS` | Same for members |
| `MODULE_NOT_FOUND` / `MODULE_AMBIGUOUS` | Same for modules |
| `CYCLE_NOT_FOUND` / `CYCLE_AMBIGUOUS` | Same for cycles |
| `WORK_ITEM_NOT_FOUND` / `WORK_ITEM_AMBIGUOUS` | Same for work items |
| `PLANE_AUTH_FAILED` | Plane rejected the API key |
| `PLANE_UNAVAILABLE` | Plane unreachable or kept returning errors after retries |
| `CAPABILITY_UNSUPPORTED` | The endpoint doesn't exist on this Plane edition |
| `VALIDATION_FAILED` | Bad input, or `PLANE_BASE_URL` / `PLANE_API_KEY` / `PLANE_WORKSPACE_SLUG` missing |
| `PARTIAL_FAILURE` | Some data couldn't be loaded; see `details` |

## How items are classified

Every work item (drafts excluded) is mapped to one state bucket from its Plane **state group**:

| Plane state group | Bucket |
|---|---|
| `backlog` | backlog |
| `unstarted` | todo |
| `started` | in progress |
| `completed` | completed |
| `cancelled` | cancelled |

Completed and cancelled are **terminal**. Flags are computed in `CLOUDSHIFT_TIMEZONE`:

| Flag | Rule |
|---|---|
| blocked | State name or any label contains "block", or a label is in `CLOUDSHIFT_BLOCKED_LABEL_NAMES` |
| overdue | Has a target date before today and isn't terminal |
| due soon | Not overdue, not terminal, and target date (end of day) within `CLOUDSHIFT_DUE_SOON_HOURS` |
| stale | Not terminal and not updated for `CLOUDSHIFT_STALE_TASK_DAYS` days |
| unassigned | No assignees |
| completed today | Completed, and `completed_at` falls on the report date |

Each metrics block contains `total`, the bucket counts, the flag counts, and `completion_percentage`, `active_percentage` (backlog + todo + in progress), `blocked_percentage`, and `overdue_percentage`.

## Health rules (workspace report)

| Level | When |
|---|---|
| `AT_RISK` | ≥ 15% overdue, or ≥ 10% blocked |
| `WATCH` | Otherwise healthy, but completion < 30% with at least 5 items |
| `HEALTHY` | None of the above |

The `reasons` field lists which rules fired. A module is listed under `at_risk_modules` when it has items and is ≥ 20% overdue, ≥ 15% blocked, or < 40% complete.

## Limitations

- **No activity history.** Plane's API has no workspace-level activity feed, so reports describe the **current** state and dates (`created_at`, `updated_at`, `completed_at`), not who changed what. For change history, call `list_work_item_activities` per item.
- **Cycle scope changes** (`scope_added_after_start`) are always `null`, with a warning: Community Edition doesn't expose reliable scope-change history.
- **Large workspaces.** Each report fetches every issue in the selected projects, paging and backing off on 429 responses. Expect slower reports on workspaces with thousands of items.

## Example prompts

- "Give me today's standup for the DEMO project."
- "What is Alex working on, and what's blocked?"
- "Weekly portfolio health across all projects. Which modules are at risk?"
- "Review Sprint 11: what's unfinished and should carry forward?"
