import asyncio
import os
import time

import httpx
from fastmcp.server.auth import TokenVerifier
from fastmcp.server.auth.auth import AccessToken
from fastmcp.utilities.logging import get_logger
from mcp.server.auth.middleware.auth_context import AuthContextMiddleware
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser, BearerAuthBackend
from starlette.authentication import AuthCredentials, AuthenticationBackend
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import HTTPConnection

from plane_mcp.claude_workspace import (
    extract_workspace_slug_from_path,
    get_workspace_from_path,
)

logger = get_logger(__name__)

DEFAULT_PLANE_BASE_URL = "https://api.plane.so"
_RETRYABLE_STATUS = {429, 502, 503, 504}


def resolve_workspace_slug(
    *,
    headers: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
    path: str | None = None,
    env_slug: str | None = None,
) -> str | None:
    """Resolve workspace for Cursor headers and Claude URL-only clients."""
    headers = headers or {}
    query_params = query_params or {}

    header_slug = (headers.get("x-workspace-slug") or headers.get("x-workspace_slug") or "").strip()
    if header_slug:
        return header_slug

    path_slug = get_workspace_from_path() or extract_workspace_slug_from_path(path or "")
    if path_slug:
        return path_slug

    for key in ("workspace_slug", "workspace"):
        value = (query_params.get(key) or "").strip()
        if value:
            return value

    fallback = env_slug if env_slug is not None else os.getenv("PLANE_WORKSPACE_SLUG", "")
    fallback = (fallback or "").strip()
    return fallback or None


class _ApiKeyOrBearerBackend(AuthenticationBackend):
    """Accept Authorization: Bearer <api-key> OR x-api-key header.

    FastMCP's default BearerAuthBackend ignores requests that only send
    x-api-key (as documented for the /http/api-key mount).
    """

    def __init__(self, token_verifier: TokenVerifier):
        self._bearer = BearerAuthBackend(token_verifier)
        self.token_verifier = token_verifier

    async def authenticate(self, conn: HTTPConnection):
        # Prefer standard Bearer flow when present.
        result = await self._bearer.authenticate(conn)
        if result is not None:
            return result

        api_key = (conn.headers.get("x-api-key") or "").strip()
        if not api_key:
            return None

        auth_info = await self.token_verifier.verify_token(api_key)
        if not auth_info:
            return None
        if auth_info.expires_at and auth_info.expires_at < int(time.time()):
            return None
        return AuthCredentials(auth_info.scopes), AuthenticatedUser(auth_info)


class PlaneHeaderAuthProvider(TokenVerifier):
    def __init__(
        self,
        required_scopes: list[str] | None = None,
        timeout_seconds: int = 10,
        max_retries: int = 3,
    ):
        super().__init__(required_scopes=required_scopes)
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def get_middleware(self) -> list:
        return [
            Middleware(
                AuthenticationMiddleware,  # type: ignore[arg-type]
                backend=_ApiKeyOrBearerBackend(self),
            ),
            Middleware(AuthContextMiddleware),  # type: ignore[arg-type]
        ]

    def _trusted_env_key_match(self, token: str, workspace_slug: str) -> bool:
        """Accept PAT when it matches the process env (same key the VPS uses for stdio).

        Used as a fallback when Plane's public API returns transient 502/503 during
        the auth probe — common on self-hosted CE behind a reverse proxy.
        """
        env_key = (os.getenv("PLANE_API_KEY") or "").strip()
        env_slug = (os.getenv("PLANE_WORKSPACE_SLUG") or "").strip()
        return bool(env_key) and token == env_key and (not env_slug or workspace_slug == env_slug)

    async def _validate_api_key(self, token: str, workspace_slug: str | None = None) -> bool:
        """Validate the API key by calling the Plane API.

        Plane Cloud / newer CE: GET /api/v1/users/me/
        Plane CE 0.23.x (CloudShift): /users/me/ may 404; fall back to workspace
        projects list which accepts X-Api-Key on verified instances.

        Important: do NOT send both ``X-Api-Key`` and ``x-api-key``. Plane CE
        treats duplicate Api-Key headers as invalid and returns 403.
        """
        base_url = (os.getenv("PLANE_INTERNAL_BASE_URL") or os.getenv("PLANE_BASE_URL", DEFAULT_PLANE_BASE_URL)).rstrip(
            "/"
        )
        # Single canonical header only — duplicate casing breaks CE 0.23.1.
        headers = {
            "X-Api-Key": token,
            "Accept": "application/json",
        }
        # Prefer projects probe first when slug is known (works on CE 0.23.1).
        probe_urls: list[str] = []
        if workspace_slug:
            probe_urls.append(f"{base_url}/api/v1/workspaces/{workspace_slug}/projects/")
        probe_urls.append(f"{base_url}/api/v1/users/me/")

        last_error: str | None = None
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                for url in probe_urls:
                    for attempt in range(self.max_retries):
                        try:
                            response = await client.get(url, headers=headers)
                        except httpx.RequestError as e:
                            last_error = f"request_error:{type(e).__name__}"
                            logger.warning("API key validation request failed (%s): %s", url, e)
                            if attempt + 1 < self.max_retries:
                                await asyncio.sleep(min(2**attempt, 4))
                                continue
                            break

                        if response.status_code == 200:
                            logger.info("API key validated via %s", url)
                            return True

                        if response.status_code in _RETRYABLE_STATUS:
                            last_error = f"http_{response.status_code}"
                            logger.warning(
                                "API key validation transient %s on %s (attempt %s/%s)",
                                response.status_code,
                                url,
                                attempt + 1,
                                self.max_retries,
                            )
                            if attempt + 1 < self.max_retries:
                                retry_after = response.headers.get("Retry-After")
                                try:
                                    delay = float(retry_after) if retry_after else min(2**attempt, 4)
                                except ValueError:
                                    delay = min(2**attempt, 4)
                                await asyncio.sleep(delay)
                                continue
                            break

                        if response.status_code == 404:
                            last_error = "http_404"
                            break  # try next probe URL

                        last_error = f"http_{response.status_code}"
                        logger.warning("API key validation failed: %s %s", response.status_code, url)
                        break  # non-retryable for this URL; try next probe

                logger.warning("API key validation failed after probes (last=%s)", last_error)
                return False
        except httpx.RequestError as e:
            logger.warning("API key validation request failed: %s", e)
            return False

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            from fastmcp.server.dependencies import get_http_headers, get_http_request

            headers = get_http_headers()
            # FastMCP may pass Bearer token; also accept explicit x-api-key.
            api_key = (token or "").strip() or (headers.get("x-api-key") or "").strip()
            if api_key.lower().startswith("bearer "):
                api_key = api_key[7:].strip()

            query_params: dict[str, str] = {}
            path = ""
            try:
                request = get_http_request()
                query_params = {k: v for k, v in request.query_params.items()}
                path = request.url.path
            except Exception:
                pass

            workspace_slug = resolve_workspace_slug(
                headers=headers,
                query_params=query_params,
                path=path,
            )

            if not api_key:
                logger.warning("API key missing (Authorization Bearer / x-api-key)")
                return None
            if not workspace_slug:
                logger.warning(
                    "Workspace slug missing — set x-workspace-slug, "
                    "?workspace_slug=, /http/api-key/w/{slug}/mcp, "
                    "or PLANE_WORKSPACE_SLUG"
                )
                return None

            validated = await self._validate_api_key(api_key, workspace_slug=workspace_slug)
            if not validated and self._trusted_env_key_match(api_key, workspace_slug):
                logger.warning(
                    "Plane auth probe failed; accepting token that matches PLANE_API_KEY env "
                    "(CloudShift CE fallback for transient Plane 502/503)"
                )
                validated = True

            if not validated:
                logger.warning("API key validation against Plane API failed")
                return None

            logger.info("API key validated successfully via Plane API (workspace=%s)", workspace_slug)
            expires_at = int(time.time() + 3600)
            return AccessToken(
                token=api_key,
                client_id="api_key_header_user",
                scopes=["read", "write"],
                expires_at=expires_at,
                claims={
                    "auth_method": "api_key_header",
                    "workspace_slug": workspace_slug,
                },
            )
        except RuntimeError:
            # No active HTTP request available (e.g., stdio transport)
            logger.debug("No active HTTP request available for header check")
            return None
