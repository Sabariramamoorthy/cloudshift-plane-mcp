# CloudShift Plane MCP

A [Model Context Protocol](https://modelcontextprotocol.io) server for [Plane](https://plane.so) that works with **self-hosted Plane Community Edition**, connects with a plain **API key over HTTP**, and adds **deterministic team reports** (daily standup, per-person, project, module, cycle, workspace).

It's built on the official [`makeplane/plane-mcp-server`](https://github.com/makeplane/plane-mcp-server) (MIT), with all 177 upstream tools kept, plus:

- **Plane CE support.** A read adapter that uses the `/issues/` API paths older Community Edition builds expose, plus retry and backoff for the 429/502/503 responses common behind self-hosted reverse proxies.
- **API-key-only HTTP mode.** Run remote HTTP without configuring a Plane OAuth app (`PLANE_MCP_DISABLE_OAUTH=true`). Clients authenticate with `Authorization: Bearer <key>` or `x-api-key`.
- **URL-scoped workspaces.** `/http/api-key/w/<workspace>/mcp` lets clients that can't send custom headers (such as Claude.ai custom connectors) pick a workspace from the URL.
- **Team reports.** Seven `cloudshift_plane_*` tools compute progress, blocked, overdue, due-soon, stale, and unassigned counts in code, not by the LLM, so numbers are reproducible.

> Not affiliated with or endorsed by Plane Software, Inc. "Plane" is a trademark of its owner.

## Contents

- [Quick start](#quick-start)
- [Connect a client](#connect-a-client)
- [Configuration](#configuration)
- [Tools](#tools)
- [Deployment](#deployment)
- [Development](#development)
- [Documentation](#documentation)
- [License and credits](#license-and-credits)

## Quick start

**Requirements:** Python 3.10+ and [uv](https://docs.astral.sh/uv/). You need a Plane workspace API token (Plane → Workspace settings → API tokens).

```bash
git clone https://github.com/Sabariramamoorthy/cloudshift-plane-mcp.git
cd cloudshift-plane-mcp
uv sync
cp .env.example .env   # then fill in PLANE_BASE_URL, PLANE_API_KEY, PLANE_WORKSPACE_SLUG
```

Run it locally over **stdio** (for Cursor, Claude Desktop, VS Code):

```bash
set -a; . ./.env; set +a
uv run plane-mcp-server stdio
```

Or as an **HTTP** server on port 8211:

```bash
set -a; . ./.env; set +a
uv run plane-mcp-server http
```

Check that it answers (an MCP `initialize` should return HTTP 200):

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8211/http/api-key/mcp \
  -H "Authorization: Bearer $PLANE_API_KEY" \
  -H "x-workspace-slug: $PLANE_WORKSPACE_SLUG" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"curl","version":"0"}}}'
```

## Connect a client

**Local (stdio)**, the simplest option for a single user:

```json
{
  "mcpServers": {
    "plane": {
      "command": "uv",
      "args": ["--directory", "/path/to/cloudshift-plane-mcp", "run", "plane-mcp-server", "stdio"],
      "env": {
        "PLANE_BASE_URL": "https://plane.example.com",
        "PLANE_API_KEY": "<your-api-key>",
        "PLANE_WORKSPACE_SLUG": "<your-workspace>"
      }
    }
  }
}
```

**Remote (HTTP)**, for clients that support headers, such as Cursor:

```json
{
  "mcpServers": {
    "plane": {
      "url": "https://mcp.example.com/http/api-key/mcp",
      "headers": {
        "Authorization": "Bearer <your-api-key>",
        "x-workspace-slug": "<your-workspace>"
      }
    }
  }
}
```

For Claude Desktop, Claude.ai custom connectors, and VS Code, see [docs/clients.md](docs/clients.md).

## Configuration

All settings are environment variables. [`.env.example`](.env.example) is a commented template. The essentials:

| Variable | Required | Purpose |
|---|---|---|
| `PLANE_BASE_URL` | yes | Your Plane URL, without `/api` (default `https://api.plane.so`) |
| `PLANE_API_KEY` | stdio, reports | Workspace API token |
| `PLANE_WORKSPACE_SLUG` | stdio, reports | Workspace slug from the Plane URL |
| `PLANE_MCP_DISABLE_OAUTH` | HTTP | `true` serves API-key routes only; no OAuth app needed |
| `PLANE_MCP_ALLOW_URL_ONLY_AUTH` | no | `true` lets credential-less requests on `/w/<slug>/mcp` use the server's key. Default `false`; read [the warning](docs/configuration.md#url-only-auth) first |
| `MCP_HOST` / `MCP_PORT` | no | HTTP bind address (default `0.0.0.0:8211`) |
| `CLOUDSHIFT_TIMEZONE` | no | IANA timezone for report dates (default `UTC`) |

The full reference, including OAuth, Redis, and report tuning, is in [docs/configuration.md](docs/configuration.md).

## Tools

**184 tools** in total:

| Group | Count | Examples |
|---|---:|---|
| Work items, comments, links, relations, activity, attachments, work logs | 40 | `list_work_items`, `retrieve_work_item_by_identifier`, `create_work_item`, `search_work_items` |
| Projects, members, estimates | 18 | `list_projects`, `get_project_members` |
| Cycles, modules, milestones | 25 | `list_cycles`, `list_module_work_items`, `transfer_cycle_work_items` |
| States, labels, types, custom properties | 31 | `list_states`, `resolve_work_item_type` |
| Workspace, users, pages, PQL | 11 | `get_workspace_members`, `get_pql_reference` |
| Initiatives, intake, releases, customers, roles | 52 | Mostly Plane Commercial/Cloud features |
| **CloudShift reports and diagnostics** | 7 | `cloudshift_plane_daily_report`, `cloudshift_plane_workspace_report` |

Full list: [docs/tools.md](docs/tools.md). Report details and output format: [docs/reports.md](docs/reports.md).

On self-hosted Community Edition, some upstream tools return 404 because the endpoint is Commercial-only or older CE builds lack it. Pages are the most common case. See [docs/self-hosted-ce.md](docs/self-hosted-ce.md) for what to expect and which tools to use instead.

## Deployment

| Option | Use when | Guide |
|---|---|---|
| Docker / Compose | You run containers | [deploy/docker-compose.yml](deploy/docker-compose.yml) |
| systemd | Long-running service on a Linux VM | [deploy/systemd/plane-mcp.service](deploy/systemd/plane-mcp.service) |
| Deploy script | Pull, install, restart, health-check on a VM | [deploy/deploy.sh](deploy/deploy.sh) |
| Reverse proxy (TLS) | Exposing to the internet | [deploy/caddy/Caddyfile.example](deploy/caddy/Caddyfile.example) |

Step-by-step instructions, including security guidance for public exposure, are in [docs/deployment.md](docs/deployment.md).

## Development

```bash
uv sync --extra dev
uv run pytest                        # unit tests; live tests skip without credentials
uv run ruff check .
uv run ruff format .
```

Integration tests against a real Plane instance: copy `.env.test` to `.env.test.local`, fill it in, and run `pytest tests/test_integration.py`. Layout and request flow are covered in [docs/architecture.md](docs/architecture.md). Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

## Documentation

| Doc | What's in it |
|---|---|
| [docs/configuration.md](docs/configuration.md) | Every environment variable |
| [docs/clients.md](docs/clients.md) | Cursor, Claude Desktop, Claude.ai, VS Code setup |
| [docs/tools.md](docs/tools.md) | All 184 tools |
| [docs/reports.md](docs/reports.md) | Report tools, metrics definitions, error codes |
| [docs/self-hosted-ce.md](docs/self-hosted-ce.md) | Community Edition compatibility and troubleshooting |
| [docs/deployment.md](docs/deployment.md) | Docker, systemd, reverse proxy, hardening |
| [docs/architecture.md](docs/architecture.md) | Code layout and request flow |

## License and credits

[MIT](LICENSE). Based on [makeplane/plane-mcp-server](https://github.com/makeplane/plane-mcp-server) by the Plane MCP Server contributors; their copyright notice is retained. CloudShift additions live mainly in [`cloudshift/`](cloudshift), [`plane_mcp/claude_workspace.py`](plane_mcp/claude_workspace.py), and the header auth provider.
