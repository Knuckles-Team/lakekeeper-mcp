# lakekeeper-mcp

A Model Context Protocol (MCP) server, A2A agent, and API client for Lakekeeper
(Apache Iceberg REST catalog) integration.

![MCP Server](https://badge.mcpx.dev?type=server 'MCP Server')

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [Usage](#usage)
- [Architecture](#architecture)
- [Environment Variables](#environment-variables)
- [MCP Tools](#mcp-tools)
- [Documentation](#documentation)

## Overview
`lakekeeper-mcp` exposes a standardized interface to a Lakekeeper (Apache Iceberg
REST catalog) deployment via the Model Context Protocol — namespace/table/
snapshot/schema-version catalog reads, warehouse admin, table ownership
classification (engine vs. Lakekeeper-native, per DEC-CA-01/GOC-78), and
maintenance-request delegation (this package never runs `expire_snapshots`/
`compact` itself — it names the delegate: Trino or Spark's own MCPs). A
Wire-First `lakekeeper_ingest_catalog` tool pushes the full catalog into the
epistemic-graph Knowledge Graph as typed OWL nodes.

Lakekeeper is the ONE live, reachable Iceberg-REST catalog on this platform —
Trino and Spark have both proven real end-to-end reads through it
(`Iceberg REST → Lakekeeper OAuth2 → SeaweedFS S3`); eg's own Iceberg-REST
catalog is not yet reachable from other pods.

Talks directly to Lakekeeper's REST APIs over `requests` — no `pyiceberg`
dependency (see [Architecture](#architecture) for why).

## Installation

Pick the extra that matches what you want to run:

| Extra | Installs | Use when |
|-------|----------|----------|
| `lakekeeper-mcp[mcp]` | Connector-focused MCP server (`agent-utilities[mcp]` — FastMCP/FastAPI + `epistemic-graph[full]`) | You only run the **MCP server** (smallest install / image) |
| `lakekeeper-mcp[agent]` | Agent runtime (`agent-utilities[agent-runtime,logfire]` — model orchestration + `epistemic-graph[full]`) | You run the **integrated A2A agent** |
| `lakekeeper-mcp[all]` | Everything (`mcp` + `agent` + `logfire`) | Development / both surfaces |

```bash
uv pip install "lakekeeper-mcp[mcp]"
```

### Container images (`:mcp` vs `:agent`)

One multi-stage `docker/Dockerfile` builds two right-sized images, selected by `--target`:

```bash
docker build --target mcp   -t lakekeeper-mcp:mcp    .
docker build --target agent -t lakekeeper-mcp:agent   .
```

## Usage
Run the MCP server directly:
```bash
python -m lakekeeper_mcp
```

### MCP Configuration Example (stdio)

```json
{
  "mcpServers": {
    "lakekeeper-mcp": {
      "command": "uv",
      "args": ["run", "lakekeeper-mcp"],
      "env": {
        "MCP_TOOL_MODE": "intent",
        "LAKEKEEPER_URL": "http://lakekeeper.arpa",
        "LAKEKEEPER_WAREHOUSE": "lakehouse",
        "LAKEKEEPERTOOL": "True",
        "LAKEKEEPER_SERVICE_CLIENT_ID": "lakekeeper-service",
        "LAKEKEEPER_SERVICE_CLIENT_SECRET": "",
        "LAKEKEEPER_OAUTH_SCOPE": "lakekeeper",
        "LAKEKEEPER_KEYCLOAK_URL": "https://keycloak.arpa",
        "LAKEKEEPER_KEYCLOAK_REALM": "homelab"
      }
    }
  }
}
```

## Architecture

`api_client.py` wraps `api/api_client_lakekeeper.py`'s `LakekeeperApi`, a thin
`requests`-based client over `api/api_client_base.py`'s fail-closed HTTP layer
(a non-JSON `2xx`, or any `>=400`, always raises — never a silent empty
result). `auth.py` mints and caches short-lived Keycloak client-credentials
tokens with `scope=lakekeeper` explicit — the shared client convention's
default (`scope=catalog`) is rejected by Lakekeeper.

**Deliberate deviation from a `pyiceberg`-SDK-based client:** `pyiceberg`
0.11.1 (latest) still pins `rich<15.0.0,>=10.11.0` in its dependency-free base
install, conflicting with this workspace's `Rich>=15` lock (a known, tracked
issue — BUG-223), and this package's brief requires zero new heavy
dependencies. A catalog CONTROL PLANE wrapper (namespace/table/snapshot/
warehouse admin) never needs Arrow-native data reads — those happen through
Trino/Spark's own MCPs — so a thin authenticated REST client (the same shape
every other fleet package in this repo uses) is the lower-risk,
template-conformant choice.

`mcp/mcp_lakekeeper.py` registers five tool groups (`catalog`, `warehouse`,
`ownership`, `maintenance`, `events`) via one `register_tool_surface(...)`
call in `mcp_server.py`, matching the fleet's one-registration-call
convention. `kg_ingest.py` exposes `ingest_entities`/`ingest_catalog` plus
record-mapping helpers around the required `native_ingest` (Wire-First)
authority.

## Environment Variables

| Variable | Required | Notes |
|----------|----------|-------|
| `LAKEKEEPER_URL` | recommended | Bare Lakekeeper origin (e.g. `http://lakekeeper.arpa`) — never including `/catalog`. Defaults to `http://lakekeeper.arpa`. |
| `LAKEKEEPER_WAREHOUSE` | recommended | Default warehouse name; every tool also accepts an explicit `warehouse` param. |
| `LAKEKEEPER_SERVICE_CLIENT_ID` | ✅ | Keycloak client-credentials client id. Defaults to `lakekeeper-service`. |
| `LAKEKEEPER_SERVICE_CLIENT_SECRET` | ✅ | Keycloak client-credentials secret. |
| `LAKEKEEPER_OAUTH_SCOPE` | optional | Defaults to `lakekeeper` — never leave at the shared-client default `catalog`. |
| `LAKEKEEPER_OAUTH_TOKEN_URL` | optional | Full token URL override; takes precedence over the Keycloak URL/realm derivation. |
| `LAKEKEEPER_KEYCLOAK_URL` | optional | Defaults to `https://keycloak.arpa`. |
| `LAKEKEEPER_KEYCLOAK_REALM` | optional | Defaults to `homelab`. |
| `LAKEKEEPER_TLS_PROFILE` / `LAKEKEEPER_TLS_PROFILE_REF` | optional | Named outbound TLS trust policy. |
| `LAKEKEEPERTOOL` | optional | Tool-group toggle (set `False` to disable the catalog/warehouse/ownership/maintenance/events tools). Default `True`. |
| `INGESTTOOL` | optional | Tool-group toggle for `lakekeeper_ingest_catalog`. Default `True`. |
| `MCP_TOOL_MODE` | optional | `condensed` \| `verbose` \| `both` \| `intent` (inherited from agent-utilities). |

## MCP Tools

| Tool | Group | Purpose |
|------|-------|---------|
| `lakekeeper_config` | catalog | Iceberg REST catalog discovery for one warehouse |
| `lakekeeper_list_namespaces` / `lakekeeper_get_namespace` | catalog | Namespace listing/read |
| `lakekeeper_list_tables` / `lakekeeper_get_table` | catalog | Table listing/read |
| `lakekeeper_list_snapshots` | catalog | Snapshot history |
| `lakekeeper_list_schema_versions` | catalog | Schema-evolution history |
| `lakekeeper_list_warehouses` / `lakekeeper_get_warehouse` | warehouse | Warehouse admin (Management API) |
| `lakekeeper_get_ownership` / `lakekeeper_set_engine_owned` | ownership | Read/classify write authority |
| `lakekeeper_maintenance_status` | maintenance | Read-only snapshot-count/age signal |
| `lakekeeper_request_expire_snapshots` / `lakekeeper_request_compaction` | maintenance | Name a delegation target; never executes |
| `lakekeeper_cloudevents_status` / `lakekeeper_cloudevents_subscribe` | events | CloudEvents sink status |
| `lakekeeper_ingest_catalog` | ingest | Wire-First KG catalog ingest |

## Documentation
See `docs/` for architecture, configuration, and deployment notes, and
`AGENTS.md` for domain-specific traps (the `/catalog/v1` root, the
`scope=lakekeeper` landmine, and the maintenance-delegation boundary).
