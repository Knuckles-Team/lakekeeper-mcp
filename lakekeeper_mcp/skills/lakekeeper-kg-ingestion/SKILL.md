---
name: lakekeeper-kg-ingestion
skill_type: skill
description: >-
  Push a Lakekeeper warehouse's Iceberg catalog into the medulla Knowledge Graph as typed OWL nodes (warehouses, namespaces, tables, snapshots, schema versions) with lakekeeper_ingest_catalog. Use to make the lakehouse catalog queryable in the KG. Do NOT use for reading or administering the catalog directly (lakekeeper-catalog-operations).
license: MIT
tags: [lakekeeper, iceberg, kg, ingest, mcp]
metadata:
  author: Knuckles-Team
  version: '0.1.0'
---
# Lakekeeper KG Ingestion

Scope: Push a Lakekeeper warehouse's Iceberg catalog into the medulla Knowledge Graph as typed OWL nodes via the lakekeeper-mcp MCP server's Wire-First ingest tool — warehouses, namespaces, tables, snapshots (with parent-snapshot lineage), and schema versions. Use when the agent must make the lakehouse catalog queryable/joinable in the KG alongside the rest of the enterprise. Do NOT use for reading/administering the catalog directly (use lakekeeper-catalog-operations).

Walks one warehouse's full catalog (namespaces -> tables -> snapshots/schema
versions) and writes it into the medulla engine as typed OWL nodes,
through the required `native_ingest` (Wire-First / `ApplyChangeEnvelope`)
authority — never a bespoke write path.

## Steps

1. Confirm the catalog is readable with `lakekeeper_list_namespaces` and verify the warehouse returns its namespaces.
2. Ingest with `lakekeeper_ingest_catalog` giving `warehouse` and `include_schemas`, and verify the response reports a count of ingested entities.
3. Check the node shape by querying the graph for `:IcebergTable` nodes, and verify ids follow `lakekeeper:<Class>:<externalId>`.
4. Confirm lineage by checking that `:IcebergSnapshot` nodes carry `parentSnapshot` links, and verify a table with several snapshots shows the chain.

## Failure recovery

| Failure | Cause | Recovery |
|---|---|---|
| `NativeIngestError` is raised | The graph engine authority is unavailable | Restore the engine connection configured for the server and call `lakekeeper_ingest_catalog` again |
| The walk stops on one table | A `get_table` read failed for that table | Fix access to that table in the catalog, because partial walks are deliberately not committed |
| Authentication error on read | The service client variables are missing | Set `LAKEKEEPER_SERVICE_CLIENT_ID` and `LAKEKEEPER_SERVICE_CLIENT_SECRET` as in `lakekeeper-catalog-operations` |

## When to use
- Make a warehouse's tables/snapshots queryable/joinable in the KG.
- Refresh the KG's view of the catalog after schema evolution or new snapshots.

## When NOT to use
- Reading/administering the catalog directly → `lakekeeper-catalog-operations`.
- Writing an engine-owned table's Iceberg pointer — this ingest tool is
  READ-projection only (DEC-CA-01); it never writes back to Lakekeeper.

## Prerequisites & environment
Same as `lakekeeper-catalog-operations` (`LAKEKEEPER_URL`,
`LAKEKEEPER_WAREHOUSE`, `LAKEKEEPER_SERVICE_CLIENT_ID`/`_SECRET`). No
additional KG-side credentials — ingestion runs through the process-owned
`GraphComputeEngine` authority.

## Tool

`lakekeeper_ingest_catalog(warehouse?, include_schemas=True)` — produces:

```
:IcebergCatalog -[hasNamespace]-> :IcebergNamespace -[hasTable]-> :IcebergTable
:IcebergTable -[hasSnapshot]-> :IcebergSnapshot -[parentSnapshot]-> :IcebergSnapshot
:IcebergTable -[storedIn]-> :LakeWarehouse
:IcebergTable -[hasSchemaVersion]-> :IcebergSchemaVersion   (when include_schemas)
```

Node ids follow `lakekeeper:<Class>:<externalId>`. Batches at ≤500 entities per
`native_ingest.ingest_entities` call (egeria-mcp's convention). Never partially
commits — `NativeIngestError` propagates rather than silently acking a partial
batch.

## Failure modes to expect
- A source read failure (e.g. one table's `get_table` call fails) propagates —
  this tool does not silently degrade a partial catalog walk to `[]`.
- The engine authority being unavailable raises `NativeIngestError`, not a
  quiet no-op.
