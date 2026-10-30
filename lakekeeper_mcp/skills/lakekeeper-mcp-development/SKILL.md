---
name: lakekeeper-mcp-development
skill_type: skill
domain: development
description: >-
  Develop, test, gate, and release the lakekeeper-mcp Iceberg REST catalog
  connector. Use this skill when changing catalog mappings, authenticated
  management calls, ownership tools, KG ingestion, packaged content, or gates.
license: MIT
tags: [lakekeeper, iceberg, catalog, development, connector, test, gates]
tier: repository
metadata:
  author: Knuckles-Team
  version: '0.1.0'
---

# lakekeeper-mcp development

This repository owns the Lakekeeper Iceberg REST and Management API facade,
OAuth2 authentication boundary, catalog/warehouse/ownership/maintenance-request
MCP tools, ontology and KG ingestion mappings, and packaged connector content.
Shared connector contracts, transports, TLS profiles, and credential helpers
belong to `scion-sdk`; admission, serving, and durable graph state
belong to their owning repositories. Read `AGENTS.md` before changing code and
keep credentials, private endpoints, tenant data, and customer records out of
source, logs, fixtures, and skill content.

## Rapid delivery: the 5-minute contract

Specs are already designed. Deliver small, reviewable slices and cite the owning
spec row in the commit trailer.

- Find the owning row first with `git grep -n "<term>" -- specs` and extend the
  existing spec before adding requirement text.
- Reuse the single `Connector` in `lakekeeper_mcp/__init__.py`, the `Api` facade
  in `lakekeeper_mcp/api_client.py`, and `LakekeeperApi` in
  `lakekeeper_mcp/api/api_client_lakekeeper.py`. Keep the shared request/TLS
  boundary in `lakekeeper_mcp/api/api_client_base.py`; do not create a second
  API, MCP, authentication, or transport plane.
- Preserve `LAKEKEEPER_URL` as the bare origin, `LAKEKEEPER_WAREHOUSE`,
  `LAKEKEEPER_SERVICE_CLIENT_ID`, `LAKEKEEPER_SERVICE_CLIENT_SECRET`,
  `LAKEKEEPER_KEYCLOAK_URL`, `LAKEKEEPER_KEYCLOAK_REALM`,
  `LAKEKEEPER_OAUTH_SCOPE`, `LAKEKEEPER_TLS_PROFILE`, and
  `LAKEKEEPER_TLS_PROFILE_REF` handling in `lakekeeper_mcp/auth.py`.
  Every OAuth2 token request must retain `scope=lakekeeper` by default; never
  print secrets or add a TLS-verification bypass.
- Keep Iceberg REST calls rooted at `/catalog/v1` and Management API calls at
  `/management/v1`. `LAKEKEEPER_URL` must stay a bare origin and must not gain a
  `/catalog` suffix. Preserve short-lived token caching and its refresh margin.
- Keep the catalog and warehouse tools, fail-closed ownership rule, and
  maintenance delegation boundary in
  `lakekeeper_mcp/mcp/mcp_lakekeeper.py`. This connector never executes
  `expire_snapshots` or compaction in-process.
- Preserve typed KG ingestion through `lakekeeper_mcp/kg_ingest.py`, source
  declarations in `lakekeeper_mcp/connector_sources.py`, and neutral ontology
  mappings. Do not introduce `pyiceberg` or another heavy dependency for this
  thin REST control-plane connector.
- Mock Lakekeeper HTTP and OAuth2 responses in local tests; never call a live
  catalog or use live credentials in a gate. Every delivered requirement needs
  a bound focused test. Generated `specs/*/status.json` files come from shared
  hooks; never hand-edit them.
- Keep `skills/**`, `ontology/**`, prompts, `mcp_config.json`, and connector
  entry points coherent with the existing package data. Do not add a second
  publisher or runtime plane.

## Setup and gates

Use the pinned environment from `uv sync --locked`, then run the shared gates:

```bash
uv sync --locked
uvx pre-commit run --all-files
uvx pre-commit run --all-files --hook-stage pre-push
```

For focused feedback, run the smallest affected tests with the locked
environment, for example:

```bash
uv run --locked --extra test pytest -q tests/test_lakekeeper_development_skill.py
uv run --locked --extra test pytest -q tests/test_api_client.py tests/test_auth_env.py
```

The canonical `.pre-commit-config.yaml` delegates connector-standard, secrets,
spec, tests-fast, and dependency-readiness to `Knuckles-Team/pipelines`. Do not
copy those hooks locally or bypass a failing check.

## Connector-specific checks

- Preserve the Iceberg REST paths, warehouse prefix resolution, table metadata
  snapshots/schemas, and Management API endpoints when changing operations.
  Add focused mocked request tests for a changed provider path.
- Keep OAuth2 client-credentials minting explicit about `scope=lakekeeper`,
  short-lived token refresh, SDK TLS profile resolution, and the configured
  Keycloak realm. Do not bake static bearer tokens into the client.
- Preserve `_ownership_of` and `_reject_if_reclassifying_native`: an existing
  `lakekeeper-native` classification is immutable and reclassification must
  fail closed. Keep maintenance tools request-only and delegated to Trino/Spark.
- Keep `lakekeeper_mcp/skills/`, `lakekeeper_mcp/ontology/`,
  `lakekeeper_mcp/connectors/`, prompts, and `lakekeeper_mcp/mcp_config.json` in
  package data. Keep ontology mappings and ingestion source metadata neutral.
- Documentation is published by the repository's existing Pages workflow and
  checked-in dashboard configuration; source status records under `specs/` are
  generated by shared hooks.

## Packaging and publication

`pyproject.toml` declares the `scion_sdk.connector` entry point
`lakekeeper-mcp = "lakekeeper_mcp:connector"` and packages `skills/**`,
`ontology/**`, `connectors/**`, prompts, and `mcp_config.json`. For a genuine
packaged-content release, keep the project version, `CHANGELOG.md`, and the
editable `lakekeeper-mcp` entry in `uv.lock` coherent, then inspect `uv build`
output for `lakekeeper_mcp/skills/lakekeeper-mcp-development/SKILL.md`.

The canonical release caller delegates publication and connector rendering to
the shared pipelines. Do not commit generated Docker artifacts or claim
package, container, or Pages publication from a local build; require exact
source hosted evidence and the public artifact.

## Delivery discipline

Work in a real Git worktree based on `origin/main`. Inspect the complete diff,
stage only reviewed paths, and verify `git status --short` after every gate. Do
not use `git stash`, `git add -A`, or `git add .`; preserve unrelated working
tree changes. Keep runtime, ontology, status, and generated artifacts outside
this bounded skill slice unless the owning requirement explicitly requires them.
