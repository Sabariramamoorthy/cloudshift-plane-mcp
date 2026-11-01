# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-01

First public release. Based on [makeplane/plane-mcp-server](https://github.com/makeplane/plane-mcp-server) 0.2.11 (all 177 upstream tools included).

### Added

- **Report tools:** `cloudshift_plane_daily_report`, `_user_report`, `_module_report`, `_project_report`, `_cycle_report`, `_workspace_report`, with metrics computed deterministically in code.
- **`cloudshift_plane_capability_report`** shows which resources a Plane instance serves.
- **Self-hosted Community Edition reader** using `/issues/` API paths, with `Retry-After`-aware backoff on 429.
- **API-key-only HTTP mode** (`PLANE_MCP_DISABLE_OAUTH=true`), so no Plane OAuth app is needed.
- **Workspace-in-URL routes** (`/http/api-key/w/<slug>/mcp`) for clients that can't send headers, plus opt-in URL-only auth (`PLANE_MCP_ALLOW_URL_ONLY_AUTH`).
- `x-api-key` header accepted alongside `Authorization: Bearer`.
- `MCP_HOST` / `MCP_PORT` settings and `plane-mcp-server --help`.
- Deployment kit: `deploy/docker-compose.yml`, systemd unit, Caddy example, and `deploy/deploy.sh`.
- Documentation under `docs/`.

### Changed

- API-key validation is compatible with Community Edition: it probes the workspace projects endpoint before `/users/me/`, sends a single `X-Api-Key` header (CE returns 403 on duplicates), and retries transient 429/502/503/504.
- Docker image includes the `cloudshift` package, runs as a non-root user, and has a health check.
- Report timezone defaults to `UTC` (`CLOUDSHIFT_TIMEZONE`).
- Live integration tests skip when `PLANE_TEST_*` credentials are absent.
- Package renamed to `cloudshift-plane-mcp` (the `plane-mcp-server` command is unchanged; `cloudshift-plane-mcp` is an alias).

### Security

- URL-only auth is **off by default**. When enabled, credential-less requests run with the server's API key; see [SECURITY.md](SECURITY.md).
