# Configuration

Everything is configured through environment variables. The server does **not** read `.env` itself. Export the variables in your shell (`set -a; . ./.env; set +a`), or pass them through Docker `env_file`, systemd `EnvironmentFile`, or your MCP client's `env` block.

## Plane connection

| Variable | Default | Description |
|---|---|---|
| `PLANE_BASE_URL` | `https://api.plane.so` | Your Plane URL **without** `/api`. The SDK appends `/api/v1`. Example: `https://plane.example.com` |
| `PLANE_API_KEY` | — | Workspace API token. Required for stdio, for the report tools, and for URL-only auth |
| `PLANE_WORKSPACE_SLUG` | — | Workspace slug, i.e. the `<slug>` in `https://plane.example.com/<slug>/projects`. Required for stdio and report tools; fallback workspace for HTTP |
| `PLANE_INTERNAL_BASE_URL` | `PLANE_BASE_URL` | Address for server-to-server calls (key validation, reports), e.g. a private network hostname. User-facing links still use `PLANE_BASE_URL` |

## HTTP server

These only apply to `plane-mcp-server http`.

| Variable | Default | Description |
|---|---|---|
| `MCP_HOST` | `0.0.0.0` | Bind address. Use `127.0.0.1` behind a reverse proxy on the same host |
| `MCP_PORT` | `8211` | Bind port |
| `MCP_PATH_PREFIX` | empty | Prefix for all routes, e.g. `/plane` when proxying under a sub-path |
| `PLANE_MCP_DISABLE_OAUTH` | `false` | `true` mounts only `/http/api-key/...` and drops the OAuth and `/.well-known` routes. Recommended unless you have configured a Plane OAuth app. Requires `PLANE_API_KEY` |
| `PLANE_MCP_ALLOW_URL_ONLY_AUTH` | `false` | See [URL-only auth](#url-only-auth) |
| `LOG_USER_INFO` | `false` | `true` adds display names (PII) to logs. User IDs and workspace slugs are always logged |

### Routes

| Route | Auth | Notes |
|---|---|---|
| `/http/api-key/mcp` | `Authorization: Bearer <key>` or `x-api-key: <key>` | Workspace from `x-workspace-slug` header, `?workspace_slug=`, or `PLANE_WORKSPACE_SLUG` |
| `/http/api-key/w/<slug>/mcp` | Same as above | Workspace taken from the path, for clients that can't send custom headers |
| `/http/mcp` | OAuth | Only when OAuth is enabled |
| `/sse` | OAuth | Legacy SSE transport; only when OAuth is enabled |

Each request's API key is validated against Plane: first `GET /api/v1/workspaces/<slug>/projects/`, then `/api/v1/users/me/`. Transient 429/502/503/504 responses are retried. If Plane stays unavailable, a key that exactly matches the server's own `PLANE_API_KEY` (and workspace) is still accepted, so a flaky Plane proxy doesn't lock out the server's own key.

### URL-only auth

When `PLANE_MCP_ALLOW_URL_ONLY_AUTH=true` and a request to `/http/api-key/w/<slug>/mcp` carries **no** credentials, the server injects its own `PLANE_API_KEY`. This lets Claude.ai custom connectors, which only accept a URL, connect without headers.

> **Warning:** with this on, **anyone who can reach that URL gets the full read/write access of `PLANE_API_KEY`**. Only enable it when the endpoint is reachable solely from a private network or VPN, or sits behind a proxy that authenticates users (SSO, basic auth, IP allowlist). Never enable it on a publicly reachable server without one of those in place.

## OAuth (optional)

Only used when `PLANE_MCP_DISABLE_OAUTH` is not `true`. You need an OAuth app registered in your Plane instance.

| Variable | Description |
|---|---|
| `PLANE_OAUTH_PROVIDER_BASE_URL` | Public URL of **this MCP server** (not Plane), e.g. `https://mcp.example.com`. The server refuses to start in OAuth mode without it |
| `PLANE_OAUTH_PROVIDER_CLIENT_ID` | OAuth app client ID |
| `PLANE_OAUTH_PROVIDER_CLIENT_SECRET` | OAuth app client secret |
| `PLANE_OAUTH_PROVIDER_ENABLE_CIMD` | `true` enables Client ID Metadata Document support |
| `PLANE_OAUTH_ALLOWED_REDIRECT_URIS` | Comma-separated redirect URI globs added to the built-in allowlist (Cursor, VS Code, Claude.ai, ChatGPT, localhost). Pin the host; wildcard only port or path |

### Token storage

OAuth tokens are kept in memory and lost on restart unless Redis is configured.

| Variable | Description |
|---|---|
| `REDIS_HOST`, `REDIS_PORT` | Redis address |
| `REDIS_PASSWORD` | Static password |
| `REDIS_SSL` | `true` for TLS |
| `ELASTICACHE_SECRET_ARN`, `REDIS_AUTH_TOKEN_KEY`, `AWS_REGION`, `AWS_SECRET_CACHE_TTL` | Rotating ElastiCache AUTH token from AWS Secrets Manager (requires IRSA or EKS Pod Identity) |

## Reports

Settings for the `cloudshift_plane_*` tools. See [reports.md](reports.md).

| Variable | Default | Description |
|---|---|---|
| `CLOUDSHIFT_TIMEZONE` | `UTC` | IANA timezone (e.g. `Europe/Berlin`, `Asia/Kolkata`) used for "today", overdue, and due-soon. Invalid values fall back to UTC |
| `CLOUDSHIFT_STALE_TASK_DAYS` | `5` | Open items not updated for this many days count as stale |
| `CLOUDSHIFT_DUE_SOON_HOURS` | `48` | Open items due within this window count as due-soon |
| `CLOUDSHIFT_BLOCKED_LABEL_NAMES` | `blocked,blocker,blocking` | Labels that mark an item blocked. Any state or label containing "block" also counts |

## Minimal setups

**Local stdio:**

```bash
PLANE_BASE_URL=https://plane.example.com
PLANE_API_KEY=plane_api_...
PLANE_WORKSPACE_SLUG=my-workspace
```

**Remote HTTP, API key only (self-hosted CE):**

```bash
PLANE_BASE_URL=https://plane.example.com
PLANE_API_KEY=plane_api_...
PLANE_WORKSPACE_SLUG=my-workspace
PLANE_MCP_DISABLE_OAUTH=true
MCP_HOST=127.0.0.1        # behind a TLS reverse proxy
CLOUDSHIFT_TIMEZONE=Europe/Berlin
```
