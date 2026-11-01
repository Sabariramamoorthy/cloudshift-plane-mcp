"""CE-specific header auth: single X-Api-Key probe (no duplicate headers)."""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from plane_mcp.auth.plane_header_auth_provider import PlaneHeaderAuthProvider


def test_validate_api_key_sends_single_x_api_key_header():
    provider = PlaneHeaderAuthProvider()
    captured: dict = {}

    async def fake_get(url, headers=None):
        captured["headers"] = dict(headers or {})
        captured["url"] = url
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        return response

    mock_client = AsyncMock()
    mock_client.get = fake_get
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    async def run():
        with patch("plane_mcp.auth.plane_header_auth_provider.httpx.AsyncClient", return_value=mock_client):
            return await provider._validate_api_key("plane_api_test", workspace_slug="demo")

    ok = asyncio.run(run())
    assert ok is True
    keys = [k.lower() for k in captured["headers"]]
    assert keys.count("x-api-key") == 1
    assert captured["headers"]["X-Api-Key"] == "plane_api_test"
    assert "x-api-key" not in captured["headers"]  # no duplicate casing
    assert "/workspaces/demo/projects/" in captured["url"]


def test_validate_api_key_retries_502_then_succeeds():
    provider = PlaneHeaderAuthProvider(max_retries=3)
    calls = {"n": 0}

    async def fake_get(url, headers=None):
        calls["n"] += 1
        response = MagicMock(spec=httpx.Response)
        response.headers = {}
        if calls["n"] < 3:
            response.status_code = 502
        else:
            response.status_code = 200
        return response

    mock_client = AsyncMock()
    mock_client.get = fake_get
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    async def run():
        with patch("plane_mcp.auth.plane_header_auth_provider.httpx.AsyncClient", return_value=mock_client):
            with patch("plane_mcp.auth.plane_header_auth_provider.asyncio.sleep", new_callable=AsyncMock):
                return await provider._validate_api_key("plane_api_test", workspace_slug="demo")

    assert asyncio.run(run()) is True
    assert calls["n"] == 3


def test_verify_token_falls_back_to_env_api_key_on_probe_failure():
    os.environ["PLANE_API_KEY"] = "plane_api_trusted"
    os.environ["PLANE_WORKSPACE_SLUG"] = "acme"
    provider = PlaneHeaderAuthProvider()

    async def run():
        with patch.object(provider, "_validate_api_key", new_callable=AsyncMock, return_value=False):
            with patch("fastmcp.server.dependencies.get_http_headers", return_value={}):
                return await provider.verify_token("plane_api_trusted")

    token = asyncio.run(run())
    assert token is not None
    assert token.claims["workspace_slug"] == "acme"


def test_validate_api_key_rejects_non_retryable():
    provider = PlaneHeaderAuthProvider(max_retries=2)

    async def fake_get(url, headers=None):
        response = MagicMock(spec=httpx.Response)
        response.status_code = 403
        response.headers = {}
        return response

    mock_client = AsyncMock()
    mock_client.get = fake_get
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    async def run():
        with patch("plane_mcp.auth.plane_header_auth_provider.httpx.AsyncClient", return_value=mock_client):
            return await provider._validate_api_key("bad", workspace_slug="demo")

    assert asyncio.run(run()) is False
