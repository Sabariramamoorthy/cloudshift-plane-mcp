# Self-hosted Plane Community Edition

The upstream tools target Plane Cloud and recent Commercial builds. Self-hosted **Community Edition (CE)** exposes a smaller public API, and older CE builds use different paths. This page lists what to expect and how to work around it.

Run `cloudshift_plane_capability_report` first. It reads a sample project and reports how many states, labels, modules, cycles, members, and issues it could load.

## What works and what doesn't

Observed on CE 0.23.1 and 1.3.1. Your build may differ; when in doubt, trust the capability report.

| Area | CE behavior | What to use |
|---|---|---|
| Projects, states, labels, cycles, modules, members (plain list endpoints) | Work | Upstream tools, or the report tools |
| `list_projects`, `list_modules`, `list_cycles` | Some CE builds return **404**: these tools call newer "lite" list endpoints | Report tools; `retrieve_project` / `retrieve_module` by ID |
| Work items (`list_work_items`, `retrieve_work_item`, comments, activity) | **404 on older CE** (≈ 0.23.x), which only exposes `/issues/` paths. Work on CE 1.x | Report tools (they always use `/issues/`) |
| `get_me` | 404 on older CE | `get_workspace_members` |
| Workspace members | 404 on older CE, works on CE 1.x | Project members, or `cloudshift_plane_user_report` |
| **Pages** | **404 on CE.** The public API doesn't include pages in Community Edition | Plane web UI |
| Initiatives, customers, releases, intake, milestones, roles, estimates | Commercial / Cloud features; 404 on CE | Not available |
| Activity history | Per work item only (`list_work_item_activities`); no workspace feed | See [reports.md § Limitations](reports.md#limitations) |

## Behaviors this fork handles

- **Duplicate API-key headers.** CE rejects requests carrying both `X-Api-Key` and `x-api-key` with **403**. The server sends exactly one canonical header.
- **Proxy errors during auth.** Self-hosted Plane behind a reverse proxy often answers 502/503 under load. Key validation retries with backoff. If Plane stays down, a request using the server's own `PLANE_API_KEY` is still accepted.
- **Rate limits.** CE API tokens are rate-limited. The report client honors `Retry-After` on 429 and backs off exponentially.
- **No `/users/me/`.** Key validation tries `GET /api/v1/workspaces/<slug>/projects/` first, which works on CE, and uses `/users/me/` only as a second probe.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Server exits: `PLANE_OAUTH_PROVIDER_BASE_URL is not set` | HTTP mode with OAuth enabled, but no OAuth app configured | Set `PLANE_MCP_DISABLE_OAUTH=true` for API-key-only mode, or configure the `PLANE_OAUTH_PROVIDER_*` variables |
| Server exits: `PLANE_API_KEY is required when PLANE_MCP_DISABLE_OAUTH=true` | API-key-only mode needs a server key | Set `PLANE_API_KEY` |
| `--host` / `--port` have no effect | The CLI takes only a mode (`stdio`, `http`, `sse`) and ignores extra flags | Use the `MCP_HOST` / `MCP_PORT` environment variables |
| `invalid_token` / 401 on `/http/api-key/mcp` | Key rejected by Plane, wrong workspace slug, or no workspace given | Check the key in Plane; send `x-workspace-slug` or use `/http/api-key/w/<slug>/mcp`; check server logs for `API key validation failed` |
| `GET /http/api-key/mcp` returns 405 | Expected: MCP requests are `POST` | Use the `curl` initialize check in the [README](../README.md#quick-start) |
| Tool returns `HTTP 404: Page not found` | Endpoint not on your CE build (see table above) | Use the listed alternative |
| Claude.ai shows an OAuth consent page for an API-key URL | OAuth discovery routes are mounted on the same host | `PLANE_MCP_DISABLE_OAUTH=true` |
| `[Errno 98] address already in use` | Another instance already holds the port | Stop it (`fuser -k 8211/tcp`) or change `MCP_PORT` |
| `ModuleNotFoundError: cloudshift` in a custom image | Image built without the `cloudshift/` package | Use the provided `Dockerfile`, which copies both packages |
| Warning about the in-memory token store | No Redis configured | Fine for API-key mode; configure Redis only for OAuth |
| Report dates look a day off | Timezone mismatch | Set `CLOUDSHIFT_TIMEZONE` to your team's IANA timezone |
