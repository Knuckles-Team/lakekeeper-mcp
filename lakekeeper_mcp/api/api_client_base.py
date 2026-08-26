"""Shared HTTP base client for the Lakekeeper (Iceberg REST catalog) API wrapper."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import urljoin

import requests
from agent_utilities.core.transport_security import (
    ResolvedTLSProfile,
    resolve_configured_tls_profile,
)


class LakekeeperApiError(RuntimeError):
    """A Lakekeeper REST/Management API call failed with a typed, non-2xx response.

    Never silently degraded to an empty result — a caller (tool layer, KG ingest)
    must be able to distinguish "table has no snapshots" from "table not found" /
    "unreachable" (lane CA-40 acceptance gate 3's explicit known-bad case).
    """

    def __init__(self, message: str, *, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class ApiClientBase:
    """Thin ``requests.Session`` wrapper with OAuth2 bearer support.

    Unlike a static-token client, ``token_provider`` (when given) is invoked on
    EVERY request so a short-lived Keycloak access token (Lakekeeper's default
    TTL is 300s, see ``lakekeeper_mcp.auth``) is refreshed transparently rather
    than baked in once at construction time.
    """

    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        token_provider: Callable[[], str] | None = None,
        tls_profile: ResolvedTLSProfile | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.token = token
        self.token_provider = token_provider
        self.timeout = timeout
        self._session = requests.Session()
        self.tls_profile = tls_profile or resolve_configured_tls_profile("lakekeeper")
        self.tls_profile.configure_requests_session(self._session)

    def _auth_header(self) -> dict[str, str]:
        if self.token_provider is not None:
            token = self.token_provider()
        else:
            token = self.token
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}

    def request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Perform an HTTP request and return parsed JSON.

        Fails closed: any non-2xx response, or a 2xx response whose body is not
        valid JSON (a hibernating/misrouted backend returning an HTML page with
        HTTP 200 is exactly the failure mode this must NOT treat as success —
        the same lesson recorded platform-wide from the ServiceNow PDI case),
        raises :class:`LakekeeperApiError` rather than degrading to ``{}``/``[]``.
        """
        if endpoint.startswith("http"):
            url = endpoint
        else:
            url = urljoin(self.base_url, endpoint.lstrip("/"))

        req_headers: dict[str, str] = {"Accept": "application/json"}
        req_headers.update(self._auth_header())
        if json_body is not None:
            req_headers["Content-Type"] = "application/json"
        if headers:
            req_headers.update(headers)

        try:
            response = self._session.request(
                method=method,
                url=url,
                headers=req_headers,
                params=params,
                json=json_body,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise LakekeeperApiError(
                f"Lakekeeper request failed (network): {method} {url}: {exc}"
            ) from exc

        if response.status_code == 204:
            return {}

        content_type = response.headers.get("Content-Type", "")
        body: Any = None
        parse_error: Exception | None = None
        stripped_text = response.text.strip()
        if stripped_text:
            # Always attempt to parse — never gate the attempt on the
            # Content-Type header. A hibernating/misrouted backend serving an
            # HTML error page with a wrong-or-missing Content-Type (and
            # possibly still HTTP 200) must be caught here, not waved through
            # because its header didn't say "json".
            try:
                body = response.json()
            except ValueError as exc:
                parse_error = exc

        if response.status_code >= 400:
            message = f"Lakekeeper API error {response.status_code}: {method} {url}"
            if isinstance(body, dict) and "error" in body:
                err = body["error"]
                if isinstance(err, dict):
                    message = (
                        f"{message} — {err.get('type', 'error')}: "
                        f"{err.get('message', '')}"
                    )
            raise LakekeeperApiError(
                message, status_code=response.status_code, body=body
            )

        if parse_error is not None:
            # 2xx but not parseable JSON — a hibernating/misrouted backend
            # returning e.g. an HTML page must never be treated as an empty
            # success result.
            raise LakekeeperApiError(
                f"Lakekeeper returned a non-JSON 2xx body (content-type={content_type!r}): "
                f"{method} {url}",
                status_code=response.status_code,
            )

        return body if body is not None else {}
