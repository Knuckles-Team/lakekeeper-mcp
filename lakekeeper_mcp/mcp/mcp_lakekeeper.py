"""Thin MCP wrappers around the Lakekeeper (Iceberg REST catalog) API client.

Each tool is a thin shim: it parses params, calls the corresponding
``LakekeeperApi`` method, and returns the result. All API surface lives in
``lakekeeper_mcp.api`` — these tools add no business logic beyond the
ownership fail-closed rule (DEC-CA-01/GOC-78) and the maintenance-delegation
boundary (this package never runs ``expire_snapshots``/``compact`` itself).

Five tool groups, per DEC-CA-08 / this lane's contract:
  * catalog     — namespaces/tables/schemas/snapshots (read-only)
  * warehouse   — warehouse list/get/storage-profile (read-only)
  * ownership   — read + classify the engine-owned-vs-Lakekeeper-native map
  * maintenance — REQUEST (never execute) expire-snapshots/compaction; status
  * events      — CloudEvents subscription status (GOC-80-W04)
"""

from __future__ import annotations

from typing import Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from lakekeeper_mcp.api.api_client_base import LakekeeperApiError
from lakekeeper_mcp.auth import get_client

_OWNERSHIP_PROPERTY = "lakekeeper-mcp.engine-owned"


def _table_status(namespace: str, table: str, warehouse: str) -> dict[str, Any]:
    """Shared read of one table's snapshot/ownership status.

    A plain module-level helper (not a call into another ``@mcp.tool``'s
    wrapped function) so the maintenance-request tools below don't depend on
    FastMCP's internal tool-object shape.
    """
    metadata = get_client().fetch_table(namespace, table, warehouse).get("metadata", {})
    snapshots = metadata.get("snapshots", [])
    return {
        "namespace": namespace,
        "table": table,
        "snapshot_count": len(snapshots),
        "current_snapshot_id": metadata.get("current-snapshot-id"),
        "owner": _ownership_of(metadata),
    }


def _reject_if_reclassifying_native(current_owner: str, requested_owner: str) -> None:
    """Fail-closed guard: refuse to reclassify a table away from 'lakekeeper-native'.

    GOC-78's single-writer map is immutable once a table is asserted
    Lakekeeper-native — this is a rejection, never a silent overwrite.
    """
    if current_owner == "lakekeeper-native" and requested_owner != "lakekeeper-native":
        raise LakekeeperApiError(
            f"refusing to reclassify away from 'lakekeeper-native' (requested "
            f"{requested_owner!r}) — GOC-78's single-writer map is immutable once "
            "a table is asserted Lakekeeper-native; this is a fail-closed "
            "rejection, not a silent overwrite"
        )


def _ownership_of(table_metadata: dict[str, Any]) -> str:
    """Read a table's ownership classification from its Iceberg properties.

    Absent classification defaults to ``lakekeeper-native`` — the safe
    default given today's reality (eg's own Iceberg-REST catalog is not yet
    reachable from other pods, CA-17/BUG-222; no table is actually
    engine-materialized yet) and matching this package's Authority note:
    Lakekeeper's own catalog metadata is authoritative unless a table has
    been explicitly classified otherwise.
    """
    props = table_metadata.get("properties", {}) or {}
    return props.get(_OWNERSHIP_PROPERTY, "lakekeeper-native")


def register_lakekeeper_tools(mcp: FastMCP) -> None:
    """Register catalog/warehouse/ownership/maintenance/events tools."""

    # ── catalog (read-only) ──────────────────────────────────────────────
    @mcp.tool(tags={"catalog"})
    async def lakekeeper_config(
        warehouse: str = Field(
            default="", description="Warehouse name (default from LAKEKEEPER_WAREHOUSE)."
        ),
    ) -> dict[str, Any]:
        """Iceberg REST catalog discovery/config for one warehouse."""
        return get_client().get_config(warehouse)

    @mcp.tool(tags={"catalog"})
    async def lakekeeper_list_namespaces(
        warehouse: str = Field(default="", description="Warehouse name."),
        parent: str = Field(
            default="", description="Optional parent namespace, for nested namespaces."
        ),
    ) -> dict[str, Any]:
        """List namespaces in a warehouse's catalog."""
        namespaces = get_client().fetch_namespaces(warehouse, parent)
        return {"namespaces": namespaces, "count": len(namespaces)}

    @mcp.tool(tags={"catalog"})
    async def lakekeeper_get_namespace(
        namespace: str = Field(description="Namespace name."),
        warehouse: str = Field(default="", description="Warehouse name."),
    ) -> dict[str, Any]:
        """Fetch one namespace's properties."""
        return get_client().fetch_namespace(namespace, warehouse)

    @mcp.tool(tags={"catalog"})
    async def lakekeeper_list_tables(
        namespace: str = Field(description="Namespace name."),
        warehouse: str = Field(default="", description="Warehouse name."),
    ) -> dict[str, Any]:
        """List tables registered under one namespace."""
        tables = get_client().fetch_tables(namespace, warehouse)
        return {"tables": tables, "count": len(tables)}

    @mcp.tool(tags={"catalog"})
    async def lakekeeper_get_table(
        namespace: str = Field(description="Namespace name."),
        table: str = Field(description="Table name."),
        warehouse: str = Field(default="", description="Warehouse name."),
    ) -> dict[str, Any]:
        """Full table load response (metadata, current schema, snapshots)."""
        return get_client().fetch_table(namespace, table, warehouse)

    @mcp.tool(tags={"catalog"})
    async def lakekeeper_list_snapshots(
        namespace: str = Field(description="Namespace name."),
        table: str = Field(description="Table name."),
        warehouse: str = Field(default="", description="Warehouse name."),
    ) -> dict[str, Any]:
        """List an Iceberg table's committed snapshots.

        A nonexistent table surfaces a typed 'table not found' error (via
        ``get_table``'s underlying 404), never an empty list — so a caller can
        tell "no such table" apart from "table has no snapshots yet".
        """
        snapshots = get_client().fetch_snapshots(namespace, table, warehouse)
        current = None
        metadata = get_client().fetch_table(namespace, table, warehouse).get("metadata", {})
        current = metadata.get("current-snapshot-id")
        return {
            "snapshots": snapshots,
            "count": len(snapshots),
            "current_snapshot_id": current,
        }

    @mcp.tool(tags={"catalog"})
    async def lakekeeper_list_schema_versions(
        namespace: str = Field(description="Namespace name."),
        table: str = Field(description="Table name."),
        warehouse: str = Field(default="", description="Warehouse name."),
    ) -> dict[str, Any]:
        """List an Iceberg table's schema-evolution history (schema ids)."""
        schemas = get_client().fetch_schema_versions(namespace, table, warehouse)
        return {"schemas": schemas, "count": len(schemas)}

    # ── warehouse (read-only) ────────────────────────────────────────────
    @mcp.tool(tags={"warehouse"})
    async def lakekeeper_list_warehouses(
        project_id: str = Field(default="", description="Optional project id filter."),
    ) -> dict[str, Any]:
        """List Lakekeeper warehouses (Management API)."""
        warehouses = get_client().fetch_warehouses(project_id)
        return {"warehouses": warehouses, "count": len(warehouses)}

    @mcp.tool(tags={"warehouse"})
    async def lakekeeper_get_warehouse(
        warehouse_id: str = Field(description="Warehouse UUID (from lakekeeper_list_warehouses)."),
    ) -> dict[str, Any]:
        """Fetch one warehouse's full record, including its storage profile."""
        return get_client().fetch_warehouse(warehouse_id)

    # ── ownership (DEC-CA-01 / GOC-78 single-writer classification) ──────
    @mcp.tool(tags={"ownership"})
    async def lakekeeper_get_ownership(
        namespace: str = Field(description="Namespace name."),
        table: str = Field(description="Table name."),
        warehouse: str = Field(default="", description="Warehouse name."),
    ) -> dict[str, Any]:
        """Read a table's ownership classification (engine vs. lakekeeper-native)."""
        metadata = get_client().fetch_table(namespace, table, warehouse).get("metadata", {})
        return {
            "namespace": namespace,
            "table": table,
            "owner": _ownership_of(metadata),
        }

    @mcp.tool(
        annotations={
            "title": "Set Table Ownership Classification",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
        tags={"ownership", "mutating"},
    )
    async def lakekeeper_set_engine_owned(
        namespace: str = Field(description="Namespace name."),
        table: str = Field(description="Table name."),
        owner: Literal["engine", "lakekeeper-native"] = Field(
            description=(
                "New ownership classification. 'engine' asserts eg redb is the "
                "authoritative source for this table's pointer (DEC-CA-01, "
                "projection-only). 'lakekeeper-native' asserts Lakekeeper's own "
                "catalog metadata is authoritative (Spark/Trino-written)."
            )
        ),
        warehouse: str = Field(default="", description="Warehouse name."),
    ) -> dict[str, Any]:
        """Classify a table's write authority — never overwrites an existing
        ``lakekeeper-native`` classification (fail closed, GOC-78's map is
        immutable once a table is asserted native; reclassifying a natively
        Lakekeeper-owned table to 'engine' would let this MCP's own writer
        claim authority over data it never wrote).

        **DEC-CA-07 note:** this is a mutating tool and, once CA-32 lands the
        rich ``actions:`` manifest block, must be declared there as a typed
        ``OntologyAction`` with ``requires_approval: true`` and
        ``conflict_policy: manual_review`` — deferred, not yet declared,
        because ``ActionSpec`` on ``main`` today only supports
        ``{id, name, description}`` (BASELINE §7; CA-32 not yet merged as of
        this lane's W1 run). The tool itself is fully implemented and callable
        now; only its typed-Action manifest declaration is pending.
        """
        client = get_client()
        current_metadata = client.fetch_table(namespace, table, warehouse).get(
            "metadata", {}
        )
        current_owner = _ownership_of(current_metadata)
        _reject_if_reclassifying_native(current_owner, owner)
        identifier = {"namespace": [namespace], "name": table}
        result = client.request(
            "POST",
            f"/catalog/v1/{client._resolve_prefix(warehouse)}/namespaces/{namespace}/tables/{table}",
            json_body={
                "identifier": identifier,
                "requirements": [],
                "updates": [
                    {
                        "action": "set-properties",
                        "updates": {_OWNERSHIP_PROPERTY: owner},
                    }
                ],
            },
        )
        return {
            "namespace": namespace,
            "table": table,
            "owner": owner,
            "previous_owner": current_owner,
            "result": result,
        }

    # ── maintenance (REQUEST only — never execute in-process) ───────────
    @mcp.tool(tags={"maintenance"})
    async def lakekeeper_maintenance_status(
        namespace: str = Field(description="Namespace name."),
        table: str = Field(description="Table name."),
        warehouse: str = Field(default="", description="Warehouse name."),
    ) -> dict[str, Any]:
        """Report a table's current snapshot count/age as maintenance-relevant signal.

        Read-only introspection only — this package never runs
        ``expire_snapshots``/``compact`` itself (this lane's explicit
        prohibited fallback); a real maintenance run must be delegated to
        Trino/Spark's own MCPs.
        """
        return _table_status(namespace, table, warehouse)

    @mcp.tool(tags={"maintenance"})
    async def lakekeeper_request_expire_snapshots(
        namespace: str = Field(description="Namespace name."),
        table: str = Field(description="Table name."),
        warehouse: str = Field(default="", description="Warehouse name."),
    ) -> dict[str, Any]:
        """Return the delegation instructions for expiring old snapshots.

        This tool DOES NOT execute ``expire_snapshots`` — it never has and
        never will run maintenance in-process (lane CA-40's explicit
        prohibited fallback). It names the delegate: Trino's
        ``sql_trino_execute`` (``ALTER TABLE ... EXECUTE expire_snapshots(...)``)
        or Spark's ``spark_submit`` procedure call, once those MCPs exist
        (CA-41/CA-42 — 'ownership' matters here: only run this against a table
        this package's own ownership map does not mark as engine-owned).
        """
        owner = _table_status(namespace, table, warehouse)["owner"]
        if owner == "engine":
            raise LakekeeperApiError(
                f"{namespace}.{table} is classified 'engine'-owned — refusing to "
                "even name a maintenance delegation target for a table this "
                "package does not own the write path for"
            )
        return {
            "namespace": namespace,
            "table": table,
            "delegate_to": "trino-mcp (sql_trino_execute) or spark-mcp (spark_submit)",
            "suggested_call": (
                f"ALTER TABLE lakehouse.{namespace}.{table} "
                "EXECUTE expire_snapshots(retention_threshold => '7d')"
            ),
            "executed_here": False,
        }

    @mcp.tool(tags={"maintenance"})
    async def lakekeeper_request_compaction(
        namespace: str = Field(description="Namespace name."),
        table: str = Field(description="Table name."),
        warehouse: str = Field(default="", description="Warehouse name."),
    ) -> dict[str, Any]:
        """Return the delegation instructions for compacting a table (never executes)."""
        owner = _table_status(namespace, table, warehouse)["owner"]
        if owner == "engine":
            raise LakekeeperApiError(
                f"{namespace}.{table} is classified 'engine'-owned — refusing to "
                "even name a maintenance delegation target for a table this "
                "package does not own the write path for"
            )
        return {
            "namespace": namespace,
            "table": table,
            "delegate_to": "trino-mcp (sql_trino_execute) or spark-mcp (spark_submit)",
            "suggested_call": (
                f"ALTER TABLE lakehouse.{namespace}.{table} EXECUTE optimize"
            ),
            "executed_here": False,
        }

    # ── events (GOC-80-W04) ──────────────────────────────────────────────
    @mcp.tool(tags={"events"})
    async def lakekeeper_cloudevents_status() -> dict[str, Any]:
        """Report whether this Lakekeeper deployment has a CloudEvents sink configured.

        Lakekeeper's Nats/Kafka CloudEvents publisher is a server-level
        deployment setting (``LAKEKEEPER__NATS_*``/``LAKEKEEPER__KAFKA_*`` env),
        not something this REST client can toggle at runtime — this tool
        reports the server info surface's queue/version fields as the closest
        live signal available without a server restart.
        """
        info = get_client().get_server_info()
        return {
            "lakekeeper_version": info.get("lakekeeper-version"),
            "queues": info.get("queues", []),
            "authz_backend": info.get("authz-backend"),
            "note": (
                "CloudEvents transport is a server-level deployment setting "
                "(LAKEKEEPER__NATS_*/LAKEKEEPER__KAFKA_*), not toggleable from "
                "this client; not configured in this deployment as of this lane."
            ),
        }

    @mcp.tool(tags={"events"})
    async def lakekeeper_cloudevents_subscribe() -> dict[str, Any]:
        """Named as a placeholder for CloudEvents subscription wiring (GOC-80-W04).

        Not implemented: Lakekeeper publishes CloudEvents to a configured
        Nats/Kafka sink, not to a per-caller webhook this MCP could subscribe
        to. A real implementation needs the sink's own consumer (kafka-mcp's
        Kafka Connect tool groups, DEC-CA-08) reading the configured topic —
        this tool documents that boundary rather than faking a subscription.
        """
        raise LakekeeperApiError(
            "lakekeeper_cloudevents_subscribe is not implemented: subscribe to "
            "the configured Nats/Kafka sink via kafka-mcp instead of this tool"
        )
