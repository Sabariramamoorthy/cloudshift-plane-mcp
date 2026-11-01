"""Main entry point for the Plane MCP Server."""

import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum

import uvicorn
from fastmcp.server.dependencies import get_access_token
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount

from plane_mcp.claude_workspace import ClaudeWorkspacePathMiddleware
from plane_mcp.server import get_header_mcp, get_oauth_mcp, get_stdio_mcp

LOG_USER_INFO: bool = os.getenv("LOG_USER_INFO", "").lower() == "true"


class UserContextFilter(logging.Filter):
    """Attach authenticated user/workspace context to every log record.

    Pulls the current request's access token via FastMCP's dependency, which
    returns None (never raises) outside a request context — so startup logs fall
    back to environment config and otherwise carry no user info.

    Always logs the opaque user id (sub claim) and the workspace slug; neither is
    PII. The display name IS PII and is only included when LOG_USER_INFO=true.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        user_id = None
        display_name = None
        workspace_slug = None
        try:
            token = get_access_token()
            if token:
                user_id = token.claims.get("sub")
                workspace_slug = token.claims.get("workspace_slug")
                if LOG_USER_INFO:
                    display_name = token.claims.get("display_name")
        except Exception as exc:
            # Never let logging enrichment break a request, but leave a signal.
            record.user_context_enrichment_error = type(exc).__name__
        record.user_id = user_id
        record.display_name = display_name
        # stdio mode has no token; fall back to the configured workspace.
        record.workspace_slug = workspace_slug or os.getenv("PLANE_WORKSPACE_SLUG") or None
        return True


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging (Datadog, ELK, etc.)."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
        }
        # The logging middleware emits a JSON object as its log message. Promote
        # those keys to top-level fields (event, method, tool, duration_ms, ...)
        raw_message = record.getMessage()
        try:
            parsed = json.loads(raw_message)
        except (ValueError, TypeError):
            parsed = None
        if isinstance(parsed, dict):
            log_entry.update(parsed)
        else:
            log_entry["message"] = raw_message
        user_id = getattr(record, "user_id", None)
        if user_id:
            log_entry["user_id"] = user_id
        workspace_slug = getattr(record, "workspace_slug", None)
        if workspace_slug:
            log_entry["workspace_slug"] = workspace_slug
        display_name = getattr(record, "display_name", None)
        if display_name:
            log_entry["display_name"] = display_name
        err = getattr(record, "user_context_enrichment_error", None)
        if err:
            log_entry["user_context_enrichment_error"] = err
        if record.exc_info and record.exc_info[1]:
            log_entry["error"] = str(record.exc_info[1])
            log_entry["error_type"] = type(record.exc_info[1]).__name__
        return json.dumps(log_entry)


def configure_json_logging():
    """Replace FastMCP's Rich handlers with a JSON formatter on the fastmcp logger."""
    fastmcp_logger = logging.getLogger("fastmcp")

    # Remove all existing handlers (Rich)
    for handler in fastmcp_logger.handlers[:]:
        fastmcp_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(UserContextFilter())
    fastmcp_logger.addHandler(handler)
    fastmcp_logger.setLevel(logging.INFO)
    fastmcp_logger.propagate = False


configure_json_logging()

logger = logging.getLogger("fastmcp.plane_mcp")


class ServerMode(Enum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"


@asynccontextmanager
async def combined_lifespan(oauth_app, header_app, sse_app):
    """Combine lifespans from both OAuth and Header MCP apps."""
    async with oauth_app.lifespan(oauth_app):
        async with header_app.lifespan(header_app):
            async with sse_app.lifespan(sse_app):
                yield


@asynccontextmanager
async def header_only_lifespan(header_app):
    """Lifespan when OAuth/SSE mounts are disabled (Claude / API-key-only hosts)."""
    async with header_app.lifespan(header_app):
        yield


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    """Run the MCP server.

    Usage:
      plane-mcp-server stdio
      plane-mcp-server http
      plane-mcp-server sse

    Host/port for HTTP are fixed at 0.0.0.0:8211 (override via reverse proxy).
    Extra flags like --help / --host / --port are not supported by upstream CLI.
    """
    if len(sys.argv) > 1 and sys.argv[1] in {"-h", "--help", "help"}:
        print(
            "Plane MCP Server\n"
            "\n"
            "Usage:\n"
            "  plane-mcp-server stdio   # local Cursor / Claude Desktop (env auth)\n"
            "  plane-mcp-server http    # HTTP API-key and/or OAuth\n"
            "\n"
            "Claude.ai (URL only — set these on the VPS):\n"
            "  PLANE_MCP_DISABLE_OAUTH=true\n"
            "  PLANE_MCP_ALLOW_URL_ONLY_AUTH=true\n"
            "  PLANE_API_KEY=...\n"
            "  URL: /http/api-key/w/{workspace_slug}/mcp\n"
        )
        return

    server_mode = ServerMode.STDIO
    if len(sys.argv) > 1:
        try:
            server_mode = ServerMode(sys.argv[1])
        except ValueError:
            print(
                f"Unknown mode {sys.argv[1]!r}. Use: stdio | http | sse\nRun: plane-mcp-server --help",
                file=sys.stderr,
            )
            raise SystemExit(2) from None

    if server_mode == ServerMode.STDIO:
        if not os.getenv("PLANE_API_KEY"):
            raise ValueError("PLANE_API_KEY is not set")
        if not os.getenv("PLANE_WORKSPACE_SLUG"):
            raise ValueError("PLANE_WORKSPACE_SLUG is not set")

        get_stdio_mcp().run()
        return

    if server_mode == ServerMode.HTTP:
        prefix = os.getenv("MCP_PATH_PREFIX") or ""
        disable_oauth = _env_flag("PLANE_MCP_DISABLE_OAUTH", default=False)
        header_app = get_header_mcp().http_app(stateless_http=True)

        if disable_oauth:
            # Claude.ai discovers OAuth via /.well-known on the same host and forces
            # the consent screen even for /http/api-key/... URLs. Mount API-key only.
            if not os.getenv("PLANE_API_KEY"):
                raise ValueError(
                    "PLANE_API_KEY is required when PLANE_MCP_DISABLE_OAUTH=true "
                    "(Claude URL-only auth injects this server key)."
                )
            app = Starlette(
                routes=[Mount(prefix + "/http/api-key", app=header_app)],
                lifespan=lambda app: header_only_lifespan(header_app),
            )
            mode_label = "API-key only (OAuth disabled)"
        else:
            oauth_base = os.getenv("PLANE_OAUTH_PROVIDER_BASE_URL")
            if not oauth_base:
                raise ValueError(
                    "PLANE_OAUTH_PROVIDER_BASE_URL is not set. "
                    "Set it to the public URL of this MCP server, or set "
                    "PLANE_MCP_DISABLE_OAUTH=true for Claude URL-only / API-key mode."
                )

            oauth_mcp = get_oauth_mcp(prefix + "/http")
            oauth_app = oauth_mcp.http_app(stateless_http=True)
            sse_mcp = get_oauth_mcp(prefix)
            sse_app = sse_mcp.http_app(transport="sse")
            oauth_well_known = oauth_mcp.auth.get_well_known_routes(mcp_path="/mcp")
            sse_well_known = sse_mcp.auth.get_well_known_routes(mcp_path="/sse")

            app = Starlette(
                routes=[
                    *oauth_well_known,
                    *sse_well_known,
                    Mount(prefix + "/http/api-key", app=header_app),
                    Mount(prefix + "/http", app=oauth_app),
                    Mount(prefix or "/", app=sse_app),
                ],
                lifespan=lambda app: combined_lifespan(oauth_app, header_app, sse_app),
            )
            mode_label = "OAuth + API-key"

        app.add_middleware(ClaudeWorkspacePathMiddleware)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        for uv_logger_name in ("uvicorn", "uvicorn.error"):
            uv_logger = logging.getLogger(uv_logger_name)
            for h in uv_logger.handlers[:]:
                uv_logger.removeHandler(h)
            uv_handler = logging.StreamHandler(sys.stderr)
            uv_handler.setFormatter(JSONFormatter())
            uv_handler.addFilter(UserContextFilter())
            uv_logger.addHandler(uv_handler)

        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8211"))
        logger.info(
            "Starting HTTP server on %s:%s — %s | PAT /http/api-key/mcp | Claude /http/api-key/w/{workspace}/mcp",
            host,
            port,
            mode_label,
        )
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=False,
        )
        return

    raise ValueError(f"Unsupported server mode: {server_mode}")


if __name__ == "__main__":
    main()
