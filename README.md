# Lakekeeper Mcp
## CLI or API | MCP | Agent

![PyPI - Version](https://img.shields.io/pypi/v/lakekeeper-mcp)
![MCP Server](https://badge.mcpx.dev?type=server 'MCP Server')
![PyPI - Downloads](https://img.shields.io/pypi/dd/lakekeeper-mcp)
![GitHub Repo stars](https://img.shields.io/github/stars/Knuckles-Team/lakekeeper-mcp)
![GitHub forks](https://img.shields.io/github/forks/Knuckles-Team/lakekeeper-mcp)
![GitHub contributors](https://img.shields.io/github/contributors/Knuckles-Team/lakekeeper-mcp)
![PyPI - License](https://img.shields.io/pypi/l/lakekeeper-mcp)
![GitHub](https://img.shields.io/github/license/Knuckles-Team/lakekeeper-mcp)
![GitHub last commit (by committer)](https://img.shields.io/github/last-commit/Knuckles-Team/lakekeeper-mcp)
![GitHub pull requests](https://img.shields.io/github/issues-pr/Knuckles-Team/lakekeeper-mcp)
![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed/Knuckles-Team/lakekeeper-mcp)
![GitHub issues](https://img.shields.io/github/issues/Knuckles-Team/lakekeeper-mcp)
![GitHub top language](https://img.shields.io/github/languages/top/Knuckles-Team/lakekeeper-mcp)
![GitHub language count](https://img.shields.io/github/languages/count/Knuckles-Team/lakekeeper-mcp)
![GitHub repo size](https://img.shields.io/github/repo-size/Knuckles-Team/lakekeeper-mcp)
![GitHub repo file count (file type)](https://img.shields.io/github/directory-file-count/Knuckles-Team/lakekeeper-mcp)
![PyPI - Wheel](https://img.shields.io/pypi/wheel/lakekeeper-mcp)
![PyPI - Implementation](https://img.shields.io/pypi/implementation/lakekeeper-mcp)

*Version: 0.1.0*

> **Documentation** — Installation, deployment, and usage across the API, CLI, MCP,
> and A2A agent interfaces are maintained in the
> [official documentation](https://knuckles-team.github.io/lakekeeper-mcp/).

---

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
        "LAKEKEEPER_URL": "http://localhost:8181",
        "LAKEKEEPER_WAREHOUSE": "lakehouse",
        "LAKEKEEPERTOOL": "True",
        "LAKEKEEPER_SERVICE_CLIENT_ID": "lakekeeper-service",
        "LAKEKEEPER_SERVICE_CLIENT_SECRET": "",
        "LAKEKEEPER_OAUTH_SCOPE": "lakekeeper",
        "LAKEKEEPER_KEYCLOAK_URL": "http://localhost:8080",
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

<!-- ENV-VARS-TABLE:START -->

#### Package environment variables

| Variable | Example | Description |
|----------|---------|-------------|
| `LAKEKEEPER_URL` | `http://localhost:8181` |  |
| `LAKEKEEPER_WAREHOUSE` | `lakehouse` |  |
| `LAKEKEEPER_SERVICE_CLIENT_ID` | `lakekeeper-service` | scope is ALWAYS "lakekeeper" explicitly — the shared client default is "catalog", which Lakekeeper rejects (services/lakekeeper/AGENTS.md). |
| `LAKEKEEPER_SERVICE_CLIENT_SECRET` | secret-injected |  |
| `LAKEKEEPER_OAUTH_SCOPE` | `lakekeeper` |  |
| `LAKEKEEPER_OAUTH_TOKEN_URL` | secret-injected | full token URL override; takes precedence |
| `LAKEKEEPER_KEYCLOAK_URL` | `http://localhost:8080` | used to derive the token URL |
| `LAKEKEEPER_KEYCLOAK_REALM` | `homelab` |  |
| `LAKEKEEPER_TLS_PROFILE` | — |  |
| `LAKEKEEPER_TLS_PROFILE_REF` | — |  |
| `LAKEKEEPERTOOL` | `True` |  |
| `INGESTTOOL` | `True` |  |

#### Inherited agent-utilities variables (apply to every connector)

| Variable | Example | Description |
|----------|---------|-------------|
| `TRANSPORT` | `stdio` | MCP transport: `stdio` \| `streamable-http` \| `sse` |
| `HOST` | `127.0.0.1` | Loopback bind host (set an authenticated ingress explicitly) |
| `PORT` | `8000` | Bind port (HTTP transports) |
| `MCP_TOOL_MODE` | `intent` | Tool surface: `intent` \| `condensed` \| `verbose` \| `both` |
| `MCP_ENABLED_TOOLS` | — | Comma-separated tool allow-list |
| `MCP_DISABLED_TOOLS` | — | Comma-separated tool deny-list |
| `MCP_ENABLED_TAGS` | — | Comma-separated tag allow-list |
| `MCP_DISABLED_TAGS` | — | Comma-separated tag deny-list |
| `EUNOMIA_TYPE` | `none` | Authorization mode: `none` \| `embedded` \| `remote` |
| `EUNOMIA_POLICY_FILE` | `mcp_policies.json` | Embedded Eunomia policy file |
| `EUNOMIA_REMOTE_URL` | — | Remote Eunomia authorization server URL |
| `ENABLE_OTEL` | `False` | Enable OpenTelemetry export |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OTLP collector endpoint |
| `MCP_CLIENT_AUTH` | — | Outbound MCP child auth: `oidc-client-credentials` \| `basic` \| `none` |
| `OIDC_CLIENT_ID` | — | OIDC client id (service-account auth) |
| `OIDC_CLIENT_SECRET_REF` | `secret://identity/oidc-client-secret` | Runtime secret reference for the OIDC service account |
| `MCP_BASIC_AUTH_USERNAME` | — | HTTP Basic username (`MCP_CLIENT_AUTH=basic`) |
| `MCP_BASIC_AUTH_PASSWORD_REF` | `secret://identity/mcp-basic-password` | Runtime secret reference for HTTP Basic auth (`MCP_CLIENT_AUTH=basic`) |
| `DEBUG` | `False` | Verbose logging |
| `PYTHONUNBUFFERED` | `1` | Unbuffered stdout (recommended in containers) |
| `MCP_URL` | `http://localhost:8000/mcp` | URL of the MCP server the agent connects to |
| `PROVIDER` | `openai` | LLM provider for the agent |
| `MODEL_ID` | `gpt-4o` | Model id for the agent |
| `ENABLE_WEB_UI` | `True` | Serve the AG-UI web interface |

_12 package + 24 inherited variable(s). Auto-generated from `.env.example` + the shared agent-utilities set — do not edit._
<!-- ENV-VARS-TABLE:END -->


| Variable | Required | Notes |
|----------|----------|-------|
| `LAKEKEEPER_URL` | recommended | Bare Lakekeeper origin (e.g. `http://localhost:8181`) — never including `/catalog`. Defaults to `http://localhost:8181`. |
| `LAKEKEEPER_WAREHOUSE` | recommended | Default warehouse name; every tool also accepts an explicit `warehouse` param. |
| `LAKEKEEPER_SERVICE_CLIENT_ID` | ✅ | Keycloak client-credentials client id. Defaults to `lakekeeper-service`. |
| `LAKEKEEPER_SERVICE_CLIENT_SECRET` | ✅ | Keycloak client-credentials secret. |
| `LAKEKEEPER_OAUTH_SCOPE` | optional | Defaults to `lakekeeper` — never leave at the shared-client default `catalog`. |
| `LAKEKEEPER_OAUTH_TOKEN_URL` | optional | Full token URL override; takes precedence over the Keycloak URL/realm derivation. |
| `LAKEKEEPER_KEYCLOAK_URL` | optional | Defaults to `http://localhost:8080`. |
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

## Available MCP Tools

<!-- MCP-TOOLS-TABLE:START -->

#### Condensed action-routed tools (`MCP_TOOL_MODE=condensed`)

| MCP Tool | Toggle Env Var | Description |
|----------|----------------|-------------|
| `lakekeeper_cloudevents_status` | `LAKEKEEPERTOOL` | Report whether this Lakekeeper deployment has a CloudEvents sink configured. |
| `lakekeeper_cloudevents_subscribe` | `LAKEKEEPERTOOL` | Named as a placeholder for CloudEvents subscription wiring (GOC-80-W04). |
| `lakekeeper_config` | `LAKEKEEPERTOOL` | Iceberg REST catalog discovery/config for one warehouse. |
| `lakekeeper_get_namespace` | `LAKEKEEPERTOOL` | Fetch one namespace's properties. |
| `lakekeeper_get_ownership` | `LAKEKEEPERTOOL` | Read a table's ownership classification (engine vs. lakekeeper-native). |
| `lakekeeper_get_table` | `LAKEKEEPERTOOL` | Full table load response (metadata, current schema, snapshots). |
| `lakekeeper_get_warehouse` | `LAKEKEEPERTOOL` | Fetch one warehouse's full record, including its storage profile. |
| `lakekeeper_ingest_catalog` | `INGESTTOOL` | Walk one warehouse's catalog and push it into the KG as typed OWL nodes. |
| `lakekeeper_list_namespaces` | `LAKEKEEPERTOOL` | List namespaces in a warehouse's catalog. |
| `lakekeeper_list_schema_versions` | `LAKEKEEPERTOOL` | List an Iceberg table's schema-evolution history (schema ids). |
| `lakekeeper_list_snapshots` | `LAKEKEEPERTOOL` | List an Iceberg table's committed snapshots. |
| `lakekeeper_list_tables` | `LAKEKEEPERTOOL` | List tables registered under one namespace. |
| `lakekeeper_list_warehouses` | `LAKEKEEPERTOOL` | List Lakekeeper warehouses (Management API). |
| `lakekeeper_maintenance_status` | `LAKEKEEPERTOOL` | Report a table's current snapshot count/age as maintenance-relevant signal. |
| `lakekeeper_request_compaction` | `LAKEKEEPERTOOL` | Return the delegation instructions for compacting a table (never executes). |
| `lakekeeper_request_expire_snapshots` | `LAKEKEEPERTOOL` | Return the delegation instructions for expiring old snapshots. |
| `lakekeeper_set_engine_owned` | `LAKEKEEPERTOOL` | Classify a table's write authority — never overwrites an existing |

#### Verbose 1:1 API-mapped tools (`MCP_TOOL_MODE=verbose` or `both`)

<details>
<summary>11 per-operation tools — one per public API method (click to expand)</summary>

| MCP Tool | Toggle Env Var | Description |
|----------|----------------|-------------|
| `lakekeeper_fetch_namespace` | `LAKEKEEPER_APITOOL` | Invoke the fetch_namespace operation. |
| `lakekeeper_fetch_namespaces` | `LAKEKEEPER_APITOOL` | Invoke the fetch_namespaces operation. |
| `lakekeeper_fetch_schema_versions` | `LAKEKEEPER_APITOOL` | Invoke the fetch_schema_versions operation. |
| `lakekeeper_fetch_snapshots` | `LAKEKEEPER_APITOOL` | Snapshot history for one table. |
| `lakekeeper_fetch_table` | `LAKEKEEPER_APITOOL` | Full table load response, including ``metadata.snapshots`` and |
| `lakekeeper_fetch_tables` | `LAKEKEEPER_APITOOL` | Invoke the fetch_tables operation. |
| `lakekeeper_fetch_warehouse` | `LAKEKEEPER_APITOOL` | Invoke the fetch_warehouse operation. |
| `lakekeeper_fetch_warehouses` | `LAKEKEEPER_APITOOL` | Invoke the fetch_warehouses operation. |
| `lakekeeper_get_config` | `LAKEKEEPER_APITOOL` | Iceberg REST catalog discovery for one warehouse. |
| `lakekeeper_get_server_info` | `LAKEKEEPER_APITOOL` | Invoke the get_server_info operation. |
| `lakekeeper_get_warehouse_storage_profile` | `LAKEKEEPER_APITOOL` | Invoke the get_warehouse_storage_profile operation. |

</details>

_17 action-routed tool(s) · 11 verbose 1:1 tool(s). Each is enabled unless its `<DOMAIN>TOOL` toggle is set false; `MCP_TOOL_MODE` selects the surface (**`intent` default** — the six verb-tools, granular set loaded on demand · `condensed` action-routed · `verbose` 1:1 · `both`). Auto-generated — do not edit._
<!-- MCP-TOOLS-TABLE:END -->

---

## Repository Owners

<img width="100%" height="180em" src="https://github-readme-stats.vercel.app/api?username=example&show_icons=true&hide_border=true&&count_private=true&include_all_commits=true" />

![GitHub followers](https://img.shields.io/github/followers/example)
![GitHub User's stars](https://img.shields.io/github/stars/example)

---

## Contribute

Contributions are welcome! Please ensure code quality by executing local checks before submitting pull requests:
- Format code using `ruff format .`
- Lint code using `ruff check .`
- Validate type-safety with `mypy .`
- Execute test suites using `pytest`


<!-- BEGIN agent-utilities-deployment (generated; do not edit between markers) -->

## Deploy with `agent-utilities-deployment`

Provision this package with the consolidated **`agent-utilities-deployment`**
workflow. It selects an installed-package, editable-source, or immutable-container
path; records only runtime secret and TLS-profile references in `AgentConfig`; and
runs doctor, registration, policy, observability, and rollback gates. Ask your agent
to **"deploy `lakekeeper-mcp` with agent-utilities-deployment"**.

| Install mode | Command |
|------|---------|
| Installed package | `uv tool install "lakekeeper-mcp[mcp]"`, then run `lakekeeper-mcp` |
| Editable source | `uv pip install -e ".[agent]"`, then run `lakekeeper-mcp` |
| Immutable container | deploy `registry.example.invalid/lakekeeper-mcp@sha256:<digest>` through the operator-selected orchestrator |

The repository embeds no deployment profile, credential value, certificate path, or
environment-specific endpoint. Supply those at runtime through `AgentConfig` and the
configured secret provider.

<!-- END agent-utilities-deployment -->

<!-- GOVERNED-CAPABILITY:START -->
## Governed capability contract

This package ships a compact canonical skill surface with specialist procedures
kept as referenced workflows. The current MCP tools, skill metadata,
`connector_manifest.yml`, ontology, mappings, shapes, fixtures, migrations,
tool-schema fingerprints, and certification metadata form one versioned
capability contract. Validate them together; do not rely on stale tool names or
historical per-task skill wrappers.

Runtime endpoints, credentials, certificate trust, tenant identity, retention,
and observability policy are deployment inputs and are never packaged values.
See [Configuration, trust, and privacy](docs/configuration.md) before enabling a
network transport, connector ingestion, GraphOS delegation, or trace export.
<!-- GOVERNED-CAPABILITY:END -->
