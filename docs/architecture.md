# Architecture

## Layers

## Why a direct REST client, not `pyiceberg`

Lakekeeper's REST surface is the standard Iceberg REST Catalog spec
(`/catalog/v1/...`) plus its own Management API (`/management/v1/...`). The
lane's original design sketch specified `pyiceberg.catalog.rest.RestCatalog`.
Two facts changed that:

1. `pyiceberg` 0.11.1 (latest, confirmed against PyPI) pins
   `rich<15.0.0,>=10.11.0` even in its dependency-free base install (no
   `pyarrow` extra) — a direct conflict with this workspace's `Rich>=15` lock
   (tracked as BUG-223).
2. This lane's brief requires **zero new heavy dependencies** in the serving
   plane. A catalog control-plane wrapper never needs Arrow-native data reads
   (those happen through Trino/Spark's own MCPs — an explicit non-goal here).

`api_client_lakekeeper.py` implements the exact REST calls a `pyiceberg`
client will make (`GET /catalog/v1/config` for prefix discovery, `GET/POST`
against `namespaces`/`tables`, `POST` against `namespaces/{ns}/tables/{t}`
for the standard `UpdateTableRequest` shape used by `lakekeeper_set_engine_owned`)
directly over `requests`, proven live against the deployed cluster.

## Fail-closed HTTP layer

`api/api_client_base.py`'s `request()` raises `LakekeeperApiError` on:
- any HTTP status `>= 400` (with the Lakekeeper error body's `type`/`message`
  folded into the exception when present),
- a `2xx` response whose body is not valid JSON (a hibernating/misrouted
  backend returning an HTML page must never look like an empty success — the
  same class of bug recorded platform-wide from the ServiceNow PDI case),
- a network-level failure (timeout, connection error).

It never returns `{}`/`[]` to paper over one of these — a caller (a tool, or
`kg_ingest.py`) can always distinguish "empty result" from "the call failed."

## Ownership classification (DEC-CA-01 / GOC-78)

A table's write-authority classification is stored as an Iceberg table
property (`lakekeeper-mcp.engine-owned`), read via `_ownership_of()` (default
`lakekeeper-native` when absent) and written via `lakekeeper_set_engine_owned`
using the standard Iceberg REST `set-properties` table-update action. The
tool refuses to reclassify a table already marked `lakekeeper-native` — see
`mcp/mcp_lakekeeper.py`'s `_reject_if_reclassifying_native`.

## Maintenance is REQUEST-only

`lakekeeper_request_expire_snapshots`/`lakekeeper_request_compaction` never
call Lakekeeper's own maintenance machinery (nor Trino/Spark) directly — they
return the exact SQL/procedure call another MCP should run, and refuse to
even name a target for an `engine`-owned table.
