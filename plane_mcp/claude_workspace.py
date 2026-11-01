"""Claude / URL-only workspace path helpers for the HTTP API-key mount.

Supports:
  https://host/http/api-key/w/{workspace_slug}/mcp

When ``PLANE_MCP_ALLOW_URL_ONLY_AUTH=true`` (default false) and the client sends no
credentials, middleware injects ``Authorization: Bearer $PLANE_API_KEY`` so Claude can
connect with the URL alone.
"""

from __future__ import annotations

import logging
import os
import re
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("planemcp.claude_workspace")

_workspace_from_path: ContextVar[str | None] = ContextVar("workspace_from_path", default=None)

_WORKSPACE_PATH_RE = re.compile(
    r"/http/api-key/w/(?P<slug>[A-Za-z0-9](?:[A-Za-z0-9_-]*[A-Za-z0-9])?)/",
)


def set_workspace_from_path(slug: str | None):
    return _workspace_from_path.set(slug)


def reset_workspace_from_path(token) -> None:
    _workspace_from_path.reset(token)


def get_workspace_from_path() -> str | None:
    return _workspace_from_path.get()


def extract_workspace_slug_from_path(path: str) -> str | None:
    match = _WORKSPACE_PATH_RE.search(path or "")
    return match.group("slug") if match else None


def rewrite_workspace_path(path: str) -> tuple[str, str | None]:
    """Rewrite /http/api-key/w/{slug}/rest → (/http/api-key/rest, slug)."""
    match = _WORKSPACE_PATH_RE.search(path or "")
    if not match:
        return path, None
    slug = match.group("slug")
    start, end = match.span()
    rewritten = path[: start + len("/http/api-key/")] + path[end:]
    return rewritten, slug


def url_only_auth_enabled() -> bool:
    # Off by default: when on, anyone who can reach the URL acts with PLANE_API_KEY.
    return os.getenv("PLANE_MCP_ALLOW_URL_ONLY_AUTH", "false").lower() in {"1", "true", "yes", "on"}


def server_api_key() -> str:
    return (os.getenv("PLANE_API_KEY") or "").strip()


def inject_authorization_header(scope: dict, api_key: str) -> None:
    headers = [(k, v) for k, v in scope.get("headers", []) if k.lower() != b"authorization"]
    headers.append((b"authorization", f"Bearer {api_key}".encode("latin-1")))
    scope["headers"] = headers


def _has_client_credentials(request: Request) -> bool:
    auth = request.headers.get("authorization")
    if auth and auth.strip():
        return True
    api_key = request.headers.get("x-api-key")
    return bool(api_key and api_key.strip())


class ClaudeWorkspacePathMiddleware(BaseHTTPMiddleware):
    """Rewrite Claude workspace URLs and optionally inject server API key."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.scope.get("path", "") or ""
        rewritten, slug = rewrite_workspace_path(path)
        if not slug:
            return await call_next(request)

        token = set_workspace_from_path(slug)
        try:
            request.scope["path"] = rewritten
            request.scope["raw_path"] = rewritten.encode("utf-8")

            if not _has_client_credentials(request) and url_only_auth_enabled():
                api_key = server_api_key()
                if api_key:
                    inject_authorization_header(request.scope, api_key)
                    logger.info("URL-only auth: injected server API key for workspace=%s", slug)
                else:
                    logger.warning(
                        "URL-only auth enabled but PLANE_API_KEY is empty (workspace=%s)",
                        slug,
                    )

            return await call_next(request)
        finally:
            reset_workspace_from_path(token)
