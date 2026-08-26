---
name: lakekeeper-catalog-operations
skill_type: skill
description: >-
  Administer a Lakekeeper (Apache Iceberg REST catalog) deployment via the
  lakekeeper-mcp MCP server's catalog/warehouse/ownership/maintenance tools —
  list/inspect namespaces, tables, snapshots, and schema versions; list/inspect
  warehouses and storage profiles; read and classify a table's write-authority
  ownership (engine vs. Lakekeeper-native, DEC-CA-01/GOC-78); and request (never
  execute) snapshot expiration or compaction. Use when the agent must inspect the
  lakehouse's Iceberg catalog state, resolve which snapshot a table is on, or
  classify who owns a table's write path. Do NOT use to run maintenance directly
  (delegate to trino-mcp/spark-mcp) or to push catalog state into the KG (use
  lakekeeper-kg-ingestion).
license: MIT
tags: [lakekeeper, iceberg, catalog, mcp]
metadata:
  author: Genius
  version: '0.1.0'
---
# Lakekeeper Catalog Operations

Read/administer the Lakekeeper Iceberg REST catalog control plane — the ONE
live, reachable Iceberg-REST catalog on this platform (Trino and Spark both
proved real reads through it; eg's own Iceberg-REST catalog is not reachable
from other pods).

## When to use
- Inspect namespaces/tables/schemas/snapshots in a warehouse (`lakekeeper_list_*`,
  `lakekeeper_get_*`).
- Resolve a table's current or historical snapshot id (`lakekeeper_list_snapshots`).
- List/inspect warehouses and their storage profiles (`lakekeeper_list_warehouses`,
  `lakekeeper_get_warehouse`).
- Read or set a table's ownership classification (`lakekeeper_get_ownership`,
  `lakekeeper_set_engine_owned`).
- Name a maintenance delegation target without running it
  (`lakekeeper_request_expire_snapshots`, `lakekeeper_request_compaction`,
  `lakekeeper_maintenance_status`).

## When NOT to use
- Actually running `expire_snapshots`/`compact` — this package never executes
  maintenance in-process; delegate to Trino's `sql_trino_execute` or Spark's
  `spark_submit` once those MCPs exist.
- Pushing catalog state into the KG → `lakekeeper-kg-ingestion`.
- Changing Lakekeeper's own authz backend (`allowall`) — CA-54's territory.

## Prerequisites & environment
Connect via the `mcp-client` skill against the **`lakekeeper-mcp`** MCP server.

| Variable | Required | Notes |
|----------|----------|-------|
| `LAKEKEEPER_URL` | ✅ | Bare Lakekeeper origin, e.g. `http://lakekeeper.arpa` (never including `/catalog`) |
| `LAKEKEEPER_WAREHOUSE` | recommended | Default warehouse name (e.g. `lakehouse`); every tool also accepts an explicit `warehouse` param |
| `LAKEKEEPER_SERVICE_CLIENT_ID` / `LAKEKEEPER_SERVICE_CLIENT_SECRET` | ✅ | Keycloak client-credentials |
| `LAKEKEEPER_OAUTH_SCOPE` | optional | Defaults to `lakekeeper` — never leave this at the shared-client default `catalog` |
| `LAKEKEEPER_KEYCLOAK_URL` / `LAKEKEEPER_KEYCLOAK_REALM` | optional | Defaults to `https://keycloak.arpa` / `homelab` |

## Tools

| Tool | Purpose |
|------|---------|
| `lakekeeper_config` | Iceberg REST catalog discovery for one warehouse |
| `lakekeeper_list_namespaces` / `lakekeeper_get_namespace` | Namespace listing/read |
| `lakekeeper_list_tables` / `lakekeeper_get_table` | Table listing/read (full metadata) |
| `lakekeeper_list_snapshots` | Snapshot history; typed error (not `[]`) for a nonexistent table |
| `lakekeeper_list_schema_versions` | Schema-evolution history |
| `lakekeeper_list_warehouses` / `lakekeeper_get_warehouse` | Warehouse admin (Management API) |
| `lakekeeper_get_ownership` / `lakekeeper_set_engine_owned` | Read/classify write authority — fails closed against overwriting an existing `lakekeeper-native` classification |
| `lakekeeper_maintenance_status` | Read-only snapshot-count/age signal |
| `lakekeeper_request_expire_snapshots` / `lakekeeper_request_compaction` | Name a delegation target; never executes |
| `lakekeeper_cloudevents_status` | Report whether a CloudEvents sink is configured |

## Failure modes to expect
- A nonexistent table/namespace raises a typed error, never an empty result.
- A hibernating/misrouted backend returning a non-JSON `200` body is treated as
  a hard failure, never a silent empty success.
- `lakekeeper_set_engine_owned` rejects reclassifying a table already marked
  `lakekeeper-native` — this is a fail-closed refusal, not a bug.
