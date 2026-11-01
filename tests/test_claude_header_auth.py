"""Tests for Claude URL-only workspace path helpers."""

from __future__ import annotations

from plane_mcp.auth.plane_header_auth_provider import resolve_workspace_slug
from plane_mcp.claude_workspace import (
    inject_authorization_header,
    rewrite_workspace_path,
    url_only_auth_enabled,
)


def test_rewrite_workspace_path():
    rewritten, slug = rewrite_workspace_path("/http/api-key/w/acme/mcp")
    assert slug == "acme"
    assert rewritten == "/http/api-key/mcp"


def test_resolve_prefers_header_then_path_then_env():
    assert (
        resolve_workspace_slug(
            headers={"x-workspace-slug": "from-header"},
            path="/http/api-key/w/from-path/mcp",
            env_slug="from-env",
        )
        == "from-header"
    )
    assert (
        resolve_workspace_slug(
            headers={},
            path="/http/api-key/w/from-path/mcp",
            env_slug="from-env",
        )
        == "from-path"
    )
    assert resolve_workspace_slug(headers={}, path="/http/api-key/mcp", env_slug="from-env") == "from-env"


def test_inject_authorization_header():
    scope = {"headers": [(b"host", b"example.com"), (b"authorization", b"Bearer old")]}
    inject_authorization_header(scope, "plane_api_new")
    assert (b"authorization", b"Bearer plane_api_new") in scope["headers"]
    assert (b"authorization", b"Bearer old") not in scope["headers"]


def test_url_only_auth_defaults_false(monkeypatch):
    monkeypatch.delenv("PLANE_MCP_ALLOW_URL_ONLY_AUTH", raising=False)
    assert url_only_auth_enabled() is False
    monkeypatch.setenv("PLANE_MCP_ALLOW_URL_ONLY_AUTH", "true")
    assert url_only_auth_enabled() is True
