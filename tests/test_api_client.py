"""Fail-closed behavior of the Lakekeeper REST client's request layer.

A hibernating/misrouted backend returning a non-JSON HTTP 200 (or any >=400
status) must raise, never degrade to an empty dict/list — the exact class of
bug this program has hit before (ServiceNow PDI returning 200+HTML on every
path) and the failure this lane's contract explicitly names.
"""

from __future__ import annotations

import pytest

from lakekeeper_mcp.api.api_client_base import ApiClientBase, LakekeeperApiError


class _FakeResponse:
    def __init__(self, status_code, text="", headers=None, json_body=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}
        self._json_body = json_body

    def json(self):
        if self._json_body is None:
            raise ValueError("no JSON body")
        return self._json_body


def _client_with_response(monkeypatch, response):
    client = ApiClientBase(base_url="http://lakekeeper.example")
    monkeypatch.setattr(client._session, "request", lambda **kwargs: response)
    return client


def test_non_json_200_raises(monkeypatch):
    """A hibernating backend returning HTML with HTTP 200 must fail closed."""
    response = _FakeResponse(
        status_code=200,
        text="<html><body>Gateway Timeout</body></html>",
        headers={"Content-Type": "text/html"},
    )
    client = _client_with_response(monkeypatch, response)

    with pytest.raises(LakekeeperApiError, match="non-JSON"):
        client.request("GET", "/catalog/v1/config")


def test_error_status_raises_with_lakekeeper_error_body(monkeypatch):
    response = _FakeResponse(
        status_code=404,
        text='{"error":{"type":"NoSuchTableException","message":"table not found","code":404}}',
        headers={"Content-Type": "application/json"},
        json_body={
            "error": {
                "type": "NoSuchTableException",
                "message": "table not found",
                "code": 404,
            }
        },
    )
    client = _client_with_response(monkeypatch, response)

    with pytest.raises(LakekeeperApiError, match="NoSuchTableException") as excinfo:
        client.request("GET", "/catalog/v1/prefix/namespaces/ns/tables/missing")
    assert excinfo.value.status_code == 404


def test_valid_json_200_returns_body(monkeypatch):
    response = _FakeResponse(
        status_code=200,
        text='{"namespaces": [["analytics"]]}',
        headers={"Content-Type": "application/json"},
        json_body={"namespaces": [["analytics"]]},
    )
    client = _client_with_response(monkeypatch, response)

    result = client.request("GET", "/catalog/v1/prefix/namespaces")

    assert result == {"namespaces": [["analytics"]]}


def test_204_returns_empty_dict(monkeypatch):
    response = _FakeResponse(status_code=204, text="")
    client = _client_with_response(monkeypatch, response)

    result = client.request("DELETE", "/catalog/v1/prefix/namespaces/ns")

    assert result == {}
