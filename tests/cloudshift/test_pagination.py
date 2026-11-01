from cloudshift.services.plane_fetch import PlaneCEClient


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.content = b"x"

    def json(self):
        return self._payload


class _FakeHttp:
    def __init__(self):
        self.calls = []

    def request(self, method, url, headers=None, params=None, **kwargs):
        self.calls.append((method, url, params))
        # two pages
        if params and params.get("cursor") == "page2":
            return _FakeResponse(
                200,
                {
                    "results": [{"id": "2"}],
                    "next_page_results": False,
                    "next_cursor": None,
                },
            )
        return _FakeResponse(
            200,
            {
                "results": [{"id": "1"}] * 100,
                "next_page_results": True,
                "next_cursor": "page2",
            },
        )

    def close(self):
        pass


def test_paginate_aggregates_all_pages():
    http = _FakeHttp()
    client = PlaneCEClient(
        base_url="https://example.test",
        api_key="plane_api_test",
        workspace_slug="slug",
        client=http,
    )
    # Force >100 items across pages to prove aggregation
    items = client.paginate("/api/v1/workspaces/slug/projects/p/issues/", per_page=100)
    assert len(items) == 101
    assert http.calls[0][2]["per_page"] == 100
    assert http.calls[1][2]["cursor"] == "page2"
