"""Plane CE 0.23.1 READ adapter (httpx). Never invent unsupported endpoints."""

from __future__ import annotations

import time
from typing import Any

import httpx

from cloudshift.config import CloudShiftConfig, plane_api_key, plane_base_url, plane_workspace_slug
from cloudshift.errors import CloudShiftError, CloudShiftErrorCode


class PlaneCEClient:
    """Request-scoped CE client with short-lived metadata cache."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        workspace_slug: str | None = None,
        config: CloudShiftConfig | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.config = config or CloudShiftConfig.from_env()
        self.base_url = (base_url or plane_base_url()).rstrip("/")
        self.api_key = api_key if api_key is not None else plane_api_key()
        self.workspace_slug = workspace_slug if workspace_slug is not None else plane_workspace_slug()
        if not self.base_url or not self.api_key or not self.workspace_slug:
            raise CloudShiftError(
                CloudShiftErrorCode.VALIDATION_FAILED,
                "PLANE_BASE_URL, PLANE_API_KEY, and PLANE_WORKSPACE_SLUG are required",
            )
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=self.config.http_timeout_seconds, follow_redirects=True)
        self._cache: dict[str, Any] = {}

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> PlaneCEClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _headers(self) -> dict[str, str]:
        return {
            "X-Api-Key": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = self._url(path)
        last_status: int | None = None
        for attempt in range(6):
            try:
                response = self._client.request(method, url, headers=self._headers(), **kwargs)
            except httpx.HTTPError as exc:
                raise CloudShiftError(
                    CloudShiftErrorCode.PLANE_UNAVAILABLE,
                    "Plane API unavailable",
                    {"reason": type(exc).__name__},
                ) from None

            last_status = response.status_code
            if response.status_code == 429:
                # Respect Plane rate limits (common on CE API tokens).
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else min(2**attempt, 20)
                except ValueError:
                    delay = min(2**attempt, 20)
                time.sleep(delay)
                continue

            if response.status_code in {401, 403}:
                raise CloudShiftError(
                    CloudShiftErrorCode.PLANE_AUTH_FAILED,
                    "Plane authentication failed",
                    {"status": response.status_code},
                )
            if response.status_code == 404:
                raise CloudShiftError(
                    CloudShiftErrorCode.CAPABILITY_UNSUPPORTED,
                    "Endpoint not available on this Plane CE instance",
                    {"path": path, "status": 404},
                )
            if response.status_code >= 400:
                raise CloudShiftError(
                    CloudShiftErrorCode.PARTIAL_FAILURE,
                    f"Plane API error HTTP {response.status_code}",
                    {"path": path, "status": response.status_code},
                )
            if response.status_code == 204 or not response.content:
                return None
            return response.json()

        raise CloudShiftError(
            CloudShiftErrorCode.PARTIAL_FAILURE,
            "Plane API rate limited after retries",
            {"path": path, "status": last_status or 429},
        )

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs)

    def paginate(self, path: str, *, params: dict[str, Any] | None = None, per_page: int = 100) -> list[dict[str, Any]]:
        """Aggregate all pages using CE cursor pagination."""
        params = dict(params or {})
        params.setdefault("per_page", per_page)
        results: list[dict[str, Any]] = []
        cursor: str | None = None
        guard = 0
        while True:
            guard += 1
            if guard > 500:
                break
            page_params = dict(params)
            if cursor:
                page_params["cursor"] = cursor
            payload = self.get(path, params=page_params)
            if isinstance(payload, list):
                results.extend(payload)
                break
            batch = payload.get("results") or []
            results.extend(batch)
            if not payload.get("next_page_results"):
                break
            cursor = payload.get("next_cursor")
            if not cursor:
                break
        return results

    # --- workspace / project metadata ---

    def list_projects(self) -> list[dict[str, Any]]:
        cache_key = "projects"
        if cache_key not in self._cache:
            path = f"/api/v1/workspaces/{self.workspace_slug}/projects/"
            self._cache[cache_key] = self.paginate(path)
        return self._cache[cache_key]

    def list_states(self, project_id: str) -> list[dict[str, Any]]:
        cache_key = f"states:{project_id}"
        if cache_key not in self._cache:
            path = f"/api/v1/workspaces/{self.workspace_slug}/projects/{project_id}/states/"
            self._cache[cache_key] = self.paginate(path)
        return self._cache[cache_key]

    def list_labels(self, project_id: str) -> list[dict[str, Any]]:
        cache_key = f"labels:{project_id}"
        if cache_key not in self._cache:
            path = f"/api/v1/workspaces/{self.workspace_slug}/projects/{project_id}/labels/"
            self._cache[cache_key] = self.paginate(path)
        return self._cache[cache_key]

    def list_modules(self, project_id: str) -> list[dict[str, Any]]:
        cache_key = f"modules:{project_id}"
        if cache_key not in self._cache:
            path = f"/api/v1/workspaces/{self.workspace_slug}/projects/{project_id}/modules/"
            self._cache[cache_key] = self.paginate(path)
        return self._cache[cache_key]

    def list_cycles(self, project_id: str) -> list[dict[str, Any]]:
        cache_key = f"cycles:{project_id}"
        if cache_key not in self._cache:
            path = f"/api/v1/workspaces/{self.workspace_slug}/projects/{project_id}/cycles/"
            self._cache[cache_key] = self.paginate(path)
        return self._cache[cache_key]

    def list_project_members(self, project_id: str) -> list[dict[str, Any]]:
        cache_key = f"members:{project_id}"
        if cache_key not in self._cache:
            path = f"/api/v1/workspaces/{self.workspace_slug}/projects/{project_id}/members/"
            payload = self.get(path)
            self._cache[cache_key] = payload if isinstance(payload, list) else (payload.get("results") or [])
        return self._cache[cache_key]

    def list_issues(self, project_id: str, *, expand: str = "assignees,labels,state") -> list[dict[str, Any]]:
        """CE uses /issues/ (not /work-items/)."""
        cache_key = f"issues:{project_id}:{expand}"
        if cache_key not in self._cache:
            path = f"/api/v1/workspaces/{self.workspace_slug}/projects/{project_id}/issues/"
            issues = self.paginate(path, params={"expand": expand} if expand else None)
            # stamp project_identifier when available
            projects = {p["id"]: p for p in self.list_projects()}
            proj = projects.get(project_id) or {}
            for issue in issues:
                issue.setdefault("project_id", project_id)
                issue.setdefault("project_identifier", proj.get("identifier"))
            self._cache[cache_key] = issues
        return self._cache[cache_key]

    def list_module_issue_ids(self, project_id: str, module_id: str) -> set[str]:
        path = f"/api/v1/workspaces/{self.workspace_slug}/projects/{project_id}/modules/{module_id}/module-issues/"
        items = self.paginate(path)
        return {str(i["id"]) for i in items if i.get("id")}

    def module_issue_map(self, project_id: str) -> dict[str, set[str]]:
        """issue_id -> set(module_id)."""
        cache_key = f"module_map:{project_id}"
        if cache_key not in self._cache:
            mapping: dict[str, set[str]] = {}
            for module in self.list_modules(project_id):
                mid = str(module["id"])
                for iid in self.list_module_issue_ids(project_id, mid):
                    mapping.setdefault(iid, set()).add(mid)
            self._cache[cache_key] = mapping
        return self._cache[cache_key]

    def list_cycle_issue_ids(self, project_id: str, cycle_id: str) -> set[str]:
        path = f"/api/v1/workspaces/{self.workspace_slug}/projects/{project_id}/cycles/{cycle_id}/cycle-issues/"
        items = self.paginate(path)
        return {str(i["id"]) for i in items if i.get("id")}

    def cycle_issue_map(self, project_id: str) -> dict[str, set[str]]:
        """issue_id -> set(cycle_id)."""
        cache_key = f"cycle_map:{project_id}"
        if cache_key not in self._cache:
            mapping: dict[str, set[str]] = {}
            for cycle in self.list_cycles(project_id):
                cid = str(cycle["id"])
                for iid in self.list_cycle_issue_ids(project_id, cid):
                    mapping.setdefault(iid, set()).add(cid)
            self._cache[cache_key] = mapping
        return self._cache[cache_key]

    def workspace_members_union(self) -> list[dict[str, Any]]:
        """CE lacks workspace members v1 path; union project members."""
        cache_key = "workspace_members"
        if cache_key not in self._cache:
            by_id: dict[str, dict[str, Any]] = {}
            for project in self.list_projects():
                if project.get("archived_at"):
                    continue
                for member in self.list_project_members(str(project["id"])):
                    mid = str(member.get("id"))
                    if mid:
                        by_id[mid] = member
            self._cache[cache_key] = list(by_id.values())
        return self._cache[cache_key]
