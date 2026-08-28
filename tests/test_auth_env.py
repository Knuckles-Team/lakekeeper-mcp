"""Auth env-var honoring and OAuth2 scope enforcement for the Lakekeeper client."""

import pytest

import lakekeeper_mcp.auth as auth_module
from lakekeeper_mcp.api.api_client_base import LakekeeperApiError


@pytest.fixture(autouse=True)
def _reset_token_cache(monkeypatch):
    """Every test gets a fresh module-level token cache."""
    monkeypatch.setattr(auth_module, "_cache", None)
    yield
    monkeypatch.setattr(auth_module, "_cache", None)


def test_get_client_honors_lakekeeper_url(monkeypatch):
    monkeypatch.setenv("LAKEKEEPER_URL", "http://lakekeeper.example")
    monkeypatch.setenv("LAKEKEEPER_WAREHOUSE", "warehouse-a")
    monkeypatch.setenv("LAKEKEEPER_SERVICE_CLIENT_SECRET", "secret")

    client = auth_module.get_client()

    assert client.base_url.rstrip("/") == "http://lakekeeper.example"
    assert client.default_warehouse == "warehouse-a"


def test_get_client_falls_back_to_default_url(monkeypatch):
    monkeypatch.delenv("LAKEKEEPER_URL", raising=False)
    monkeypatch.setenv("LAKEKEEPER_SERVICE_CLIENT_SECRET", "secret")

    client = auth_module.get_client()

    assert client.base_url.rstrip("/") == "http://localhost:8181"


def test_token_cache_requires_client_secret(monkeypatch):
    monkeypatch.delenv("LAKEKEEPER_SERVICE_CLIENT_SECRET", raising=False)

    with pytest.raises(LakekeeperApiError, match="LAKEKEEPER_SERVICE_CLIENT_SECRET"):
        auth_module.get_token()


def test_token_mint_sends_explicit_scope(monkeypatch):
    """The landmine this module exists to avoid: never the shared-client default scope."""
    monkeypatch.setenv("LAKEKEEPER_SERVICE_CLIENT_SECRET", "secret")
    captured = {}

    class _FakeResponse:
        status_code = 200

        def json(self):
            return {
                "access_token": "tok-123",
                "expires_in": 300,
                "scope": "lakekeeper profile",
            }

    def _fake_post(url, data=None, timeout=None, verify=None):
        captured["url"] = url
        captured["data"] = data
        return _FakeResponse()

    monkeypatch.setattr(auth_module.requests, "post", _fake_post)

    token = auth_module.get_token()

    assert token == "tok-123"
    assert captured["data"]["scope"] == "lakekeeper"
    assert captured["data"]["grant_type"] == "client_credentials"


def test_token_mint_rejects_unexpected_granted_scope(monkeypatch):
    """A token minted with scope=catalog (or anything not including 'lakekeeper') is refused."""
    monkeypatch.setenv("LAKEKEEPER_SERVICE_CLIENT_SECRET", "secret")

    class _FakeResponse:
        status_code = 200

        def json(self):
            return {
                "access_token": "tok-123",
                "expires_in": 300,
                "scope": "catalog profile",
            }

    monkeypatch.setattr(auth_module.requests, "post", lambda *_, **__: _FakeResponse())

    with pytest.raises(LakekeeperApiError, match="scope"):
        auth_module.get_token()


def test_token_cache_reuses_unexpired_token(monkeypatch):
    monkeypatch.setenv("LAKEKEEPER_SERVICE_CLIENT_SECRET", "secret")
    calls = {"n": 0}

    class _FakeResponse:
        status_code = 200

        def json(self):
            calls["n"] += 1
            return {
                "access_token": f"tok-{calls['n']}",
                "expires_in": 300,
                "scope": "lakekeeper",
            }

    monkeypatch.setattr(auth_module.requests, "post", lambda *_, **__: _FakeResponse())

    first = auth_module.get_token()
    second = auth_module.get_token()

    assert first == second == "tok-1"
    assert calls["n"] == 1
