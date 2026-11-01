# Deployment

Local use needs no deployment: run `plane-mcp-server stdio` from your MCP client (see [clients.md](clients.md)). This page covers running the **HTTP** server for remote or shared use.

All options read configuration from `.env` (copy [`.env.example`](../.env.example)). For API-key-only mode, which needs no Plane OAuth app, set:

```bash
PLANE_BASE_URL=https://plane.example.com
PLANE_API_KEY=plane_api_...
PLANE_WORKSPACE_SLUG=my-workspace
PLANE_MCP_DISABLE_OAUTH=true
```

## Option 1: Docker Compose

```bash
git clone https://github.com/Sabariramamoorthy/cloudshift-plane-mcp.git
cd cloudshift-plane-mcp
cp .env.example .env      # fill in
docker compose -f deploy/docker-compose.yml up -d --build
docker compose -f deploy/docker-compose.yml logs -f
```

The container runs as a non-root user with a read-only filesystem and a health check, and publishes only on `127.0.0.1:8211`. Put a TLS reverse proxy in front (Option 4).

Plain Docker:

```bash
docker build -t cloudshift-plane-mcp .
docker run -d --name plane-mcp --env-file .env -p 127.0.0.1:8211:8211 --read-only --tmpfs /tmp cloudshift-plane-mcp
```

## Option 2: systemd on a Linux host

```bash
sudo useradd --system --create-home --home-dir /var/lib/plane-mcp --shell /usr/sbin/nologin plane-mcp
sudo install -d -o plane-mcp -g plane-mcp /opt/cloudshift-plane-mcp
sudo -u plane-mcp git clone https://github.com/Sabariramamoorthy/cloudshift-plane-mcp.git /opt/cloudshift-plane-mcp
cd /opt/cloudshift-plane-mcp
sudo -u plane-mcp -H bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
sudo -u plane-mcp -H /var/lib/plane-mcp/.local/bin/uv sync --frozen --no-dev
sudo -u plane-mcp cp .env.example .env && sudo -u plane-mcp chmod 600 .env   # then edit .env

sudo cp deploy/systemd/plane-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now plane-mcp
journalctl -u plane-mcp -f
```

The unit file assumes `/opt/cloudshift-plane-mcp` and a `plane-mcp` user. Adjust with `sudo systemctl edit plane-mcp`.

## Option 3: `deploy/deploy.sh`

For hosts where you `git pull` new versions. The script:

1. Loads `.env` and checks the required variables.
2. Runs `git pull --ff-only` (skip with `SKIP_PULL=true`).
3. Runs `uv sync --frozen --no-dev` **as the app user**, even when started with `sudo`, so `.venv` is never root-owned.
4. Restarts the `plane-mcp` systemd unit if one exists. Otherwise it stops its own previous instance (PID file, then the configured port) and starts the server with `nohup`.
5. Sends an MCP `initialize` with the server key and fails unless Plane accepts it (HTTP 200).

```bash
deploy/deploy.sh
# or: APP_DIR=/opt/cloudshift-plane-mcp SERVICE_NAME=plane-mcp sudo -E deploy/deploy.sh
```

| Variable | Default | Purpose |
|---|---|---|
| `APP_DIR` | repository root | Where the app and `.env` live |
| `RUN_USER` | invoking user (`SUDO_USER` under sudo) | User that owns and runs the app; root is refused |
| `SERVICE_NAME` | `plane-mcp` | systemd unit to restart if present |
| `LOG_DIR` | `$APP_DIR/logs` | Log location when not using systemd |
| `SKIP_PULL` | `false` | Skip `git pull` |
| `HEALTH_RETRIES` | `10` | Health-check attempts, 3 s apart |

## Option 4: Reverse proxy and TLS

Run the server on loopback (`MCP_HOST=127.0.0.1`, or the Compose port binding) and terminate TLS in a proxy. [`deploy/caddy/Caddyfile.example`](../deploy/caddy/Caddyfile.example) is a ready-made Caddy site with streaming enabled. For nginx, disable buffering for MCP streams:

```nginx
location / {
    proxy_pass http://127.0.0.1:8211;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_read_timeout 300s;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Serving under a sub-path such as `/plane/`? Set `MCP_PATH_PREFIX=/plane` and proxy that path unchanged.

## Exposure checklist

Before making the server reachable from the internet:

- [ ] TLS terminates in front of the server; port 8211 isn't publicly reachable.
- [ ] `PLANE_MCP_ALLOW_URL_ONLY_AUTH` is `false`, **or** the proxy authenticates users or restricts source IPs. With URL-only auth on, anyone who can reach `/http/api-key/w/<slug>/mcp` acts with the server's API key.
- [ ] `.env` is readable only by the service user (`chmod 600`) and isn't committed.
- [ ] `PLANE_API_KEY` belongs to an account with only the access the team needs. Report tools always use this key (see [reports.md](reports.md)).
- [ ] One server per workspace or team. Don't share a server across organizations.
- [ ] `LOG_USER_INFO` stays `false` unless you need display names in logs.

## Verifying

```bash
set -a; . ./.env; set +a
curl -s -o /dev/null -w "%{http_code}\n" -X POST "https://mcp.example.com/http/api-key/mcp" \
  -H "Authorization: Bearer $PLANE_API_KEY" -H "x-workspace-slug: $PLANE_WORKSPACE_SLUG" \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"curl","version":"0"}}}'
```

`200` means the server is up and Plane accepted the key. `401` means the key or workspace slug was rejected. A plain `GET` returning `405` is expected. For other symptoms, see [self-hosted-ce.md § Troubleshooting](self-hosted-ce.md#troubleshooting).
