# Configuration

See the [README's Environment Variables table](../README.md#environment-variables)
for the full, authoritative list — the code (`auth.py`, `mcp/mcp_lakekeeper.py`,
`kg_ingest.py`) is the source of truth; `.env.example`, every `mcp_config*.json`,
`docker/*compose*.yml`, and this table must all match it exactly (enforced by
`python -m agent_utilities.mcp.check_env_var_drift --check`).

## The `scope=lakekeeper` landmine

Lakekeeper's Keycloak client (`lakekeeper-service`) is provisioned for
`scope=lakekeeper`. The shared Iceberg-REST/OAuth2 client convention many SDKs
default to is `scope=catalog` — a token minted with that default is silently
rejected. `auth.py` passes `scope=lakekeeper` explicitly on every token
request and additionally verifies the **granted** scope includes it,
rejecting the token outright otherwise (fail closed, not a delayed 403 three
calls later).

## The `/catalog/v1` root

`LAKEKEEPER_URL` is the bare Lakekeeper origin (e.g. `http://localhost:8181`)
— **never** including `/catalog`. The client appends `/catalog/v1/...` (Iceberg
REST) and `/management/v1/...` (Lakekeeper's own Management API) itself.
Pointing this env var at `.../catalog` is the most common first-time
misconfiguration and presents as a confusing 404, not an auth error.

## TLS

`LAKEKEEPER_TLS_PROFILE`/`LAKEKEEPER_TLS_PROFILE_REF` select a named outbound
TLS trust policy (via `agent_utilities.core.transport_security`). The
homelab's internal CA (`homelab-arpa-ca`) is trusted fleet-wide via the
`homelab-ca-bundle` ConfigMap mount; Lakekeeper itself is served over plain
HTTP at the ingress (`http://localhost:8181`) — only Keycloak enforces a
TLS redirect.
