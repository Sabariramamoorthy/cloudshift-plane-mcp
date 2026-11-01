# Connecting MCP clients

Replace `https://mcp.example.com` with where you host the server, `<your-api-key>` with a Plane workspace API token, and `<your-workspace>` with your workspace slug.

Use **stdio** when the client runs on the same machine and only you use it. Use **HTTP** for a shared or remote server; it needs `PLANE_MCP_DISABLE_OAUTH=true` unless you have set up OAuth (see [configuration.md](configuration.md)).

## Cursor

`~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (per project).

Remote HTTP:

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

Local stdio:

```json
{
  "mcpServers": {
    "plane": {
      "command": "uv",
      "args": ["--directory", "/path/to/cloudshift-plane-mcp", "run", "plane-mcp-server", "stdio"],
      "env": {
        "PLANE_BASE_URL": "https://plane.example.com",
        "PLANE_API_KEY": "<your-api-key>",
        "PLANE_WORKSPACE_SLUG": "<your-workspace>",
        "CLOUDSHIFT_TIMEZONE": "UTC"
      }
    }
  }
}
```

## VS Code (GitHub Copilot agent mode)

`.vscode/mcp.json`:

```json
{
  "servers": {
    "plane": {
      "type": "http",
      "url": "https://mcp.example.com/http/api-key/mcp",
      "headers": {
        "Authorization": "Bearer ${input:plane-api-key}",
        "x-workspace-slug": "<your-workspace>"
      }
    }
  },
  "inputs": [
    { "id": "plane-api-key", "type": "promptString", "description": "Plane API key", "password": true }
  ]
}
```

## Claude Code

```bash
claude mcp add --transport http plane https://mcp.example.com/http/api-key/mcp \
  --header "Authorization: Bearer <your-api-key>" \
  --header "x-workspace-slug: <your-workspace>"
```

## Claude Desktop

Claude Desktop's config file launches local commands. Use stdio (same block as Cursor above), or bridge to a remote server with [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) (Node.js 18+):

```json
{
  "mcpServers": {
    "plane": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote@latest",
        "https://mcp.example.com/http/api-key/w/<your-workspace>/mcp",
        "--header", "Authorization:Bearer ${PLANE_API_KEY}"
      ],
      "env": { "PLANE_API_KEY": "<your-api-key>" }
    }
  }
}
```

## Claude.ai (custom connectors)

Custom connectors accept only a URL, with no custom headers. Two options:

1. **Recommended:** put the server behind a proxy that authenticates users (SSO, VPN, IP allowlist), and enable URL-only auth so requests that reach the server use its own key:

   ```bash
   PLANE_MCP_DISABLE_OAUTH=true          # stops Claude.ai from sending you to an OAuth consent screen
   PLANE_MCP_ALLOW_URL_ONLY_AUTH=true
   ```

   Connector URL: `https://mcp.example.com/http/api-key/w/<your-workspace>/mcp`

2. **OAuth:** configure a Plane OAuth app and the `PLANE_OAUTH_PROVIDER_*` variables, then use `https://mcp.example.com/http/mcp`.

> **Warning:** URL-only auth gives anyone who can reach the URL the access of the server's `PLANE_API_KEY`. Read [configuration.md § URL-only auth](configuration.md#url-only-auth) before enabling it.

## Checking a connection

Ask the agent to "list my Plane projects". It should call `list_projects`. On older self-hosted Community Edition builds that tool may return 404; `cloudshift_plane_capability_report` shows what your instance supports. See [self-hosted-ce.md](self-hosted-ce.md).
