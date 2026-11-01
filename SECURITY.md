# Security policy

## Reporting a vulnerability

**Please don't open a public issue.** Report privately through GitHub: [Report a vulnerability](https://github.com/Sabariramamoorthy/cloudshift-plane-mcp/security/advisories/new).

Include the affected version or commit, steps to reproduce, and the impact you expect. We aim to acknowledge reports within 5 business days and will keep you updated until a fix is released. With your permission, we'll credit you in the advisory.

If the issue is in upstream code that this fork hasn't modified, please also report it to Plane: [makeplane/plane-mcp-server security advisories](https://github.com/makeplane/plane-mcp-server/security/advisories/new).

## Supported versions

Only the latest release on `main` receives security fixes.

## Scope

In scope:

- Authentication bypass on the HTTP routes (`/http/api-key/...`, `/http/mcp`, `/sse`)
- Leaking API keys, OAuth tokens, or workspace data across users or workspaces
- Server-side request forgery (for example via attachment upload URLs)
- Injection in tool inputs that reaches Plane or the host

Out of scope:

- Behavior that follows from documented configuration, such as enabling `PLANE_MCP_ALLOW_URL_ONLY_AUTH` on a public server (see below)
- Vulnerabilities in Plane itself; report those to Plane
- Denial of service from unauthenticated request volume (rate-limit at your proxy)

## Security model: what operators should know

- **API keys are bearer credentials.** Each HTTP request carries a Plane API key, and the server acts with exactly that key's permissions. Always serve HTTP over TLS.
- **URL-only auth is off by default.** With `PLANE_MCP_ALLOW_URL_ONLY_AUTH=true`, requests without credentials to `/http/api-key/w/<slug>/mcp` run with the **server's** `PLANE_API_KEY`. Enable it only behind a network boundary or an authenticating proxy.
- **Report tools use the server's key.** `cloudshift_plane_*` tools read Plane with `PLANE_API_KEY` / `PLANE_WORKSPACE_SLUG` from the server environment, regardless of who calls them. Run one server per team or workspace.
- **Fallback acceptance.** If Plane is temporarily unreachable (502/503), a request whose key exactly matches the server's `PLANE_API_KEY` is still accepted. Other keys are rejected.
- **Logs** never contain API keys. Display names are logged only with `LOG_USER_INFO=true`.
