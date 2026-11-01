import pytest

from cloudshift.errors import CloudShiftError, CloudShiftErrorCode
from cloudshift.services.plane_fetch import PlaneCEClient


class _Resp:
    def __init__(self, code, payload=None):
        self.status_code = code
        self._payload = payload or {}
        self.content = b"{}" if payload is not None else b""

    def json(self):
        return self._payload


class _Http:
    def __init__(self, code):
        self.code = code

    def request(self, *args, **kwargs):
        return _Resp(self.code, {"error": "x"})

    def close(self):
        pass


def test_auth_failed_mapping():
    client = PlaneCEClient(
        base_url="https://example.test",
        api_key="k",
        workspace_slug="s",
        client=_Http(401),
    )
    with pytest.raises(CloudShiftError) as exc:
        client.get("/api/v1/x")
    assert exc.value.code == CloudShiftErrorCode.PLANE_AUTH_FAILED


def test_unsupported_mapping():
    client = PlaneCEClient(
        base_url="https://example.test",
        api_key="k",
        workspace_slug="s",
        client=_Http(404),
    )
    with pytest.raises(CloudShiftError) as exc:
        client.get("/api/v1/users/me/")
    assert exc.value.code == CloudShiftErrorCode.CAPABILITY_UNSUPPORTED
