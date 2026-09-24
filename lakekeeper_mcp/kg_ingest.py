"""Native epistemic-graph ingestion for the Lakekeeper Iceberg catalog.

CONCEPT:AU-KG.ingest.enterprise-source-extractor. The record-source twin of the
egeria/jena connectors: lakekeeper-mcp natively pushes the ONE live, reachable
Iceberg-REST catalog (Trino/Spark's sibling lanes CA-52/CA-53 both proved real
reads through this exact path — eg's own Iceberg-REST catalog is not reachable
from other pods, CA-17/BUG-222) into the epistemic-graph engine as typed OWL
nodes (``:LakeWarehouse``, ``:IcebergCatalog``, ``:IcebergNamespace``,
``:IcebergTable``, ``:IcebergSnapshot``, ``:IcebergSchemaVersion``), with
``hasNamespace``/``hasTable``/``hasSnapshot``/``parentSnapshot``/``storedIn``/
``hasSchemaVersion`` relations.

The txn write path is the required
``agent_utilities.knowledge_graph.memory.native_ingest`` authority. Node ids
follow ``lakekeeper:<class>:<externalId>``; ``node_type`` on each entity
matches a class federated by ``lakekeeper_mcp.ontology`` (``lakekeeper.ttl``).
Batches at ≤500 entities per ``ingest_entities`` call (egeria-mcp's convention).
"""

from __future__ import annotations

import logging
from typing import Any

from agent_utilities.knowledge_graph.memory.native_ingest import (
    ingest_entities as _native_ingest_entities,
)
from fastmcp import FastMCP
from pydantic import Field

from lakekeeper_mcp.auth import get_client

logger = logging.getLogger("lakekeeper_mcp.kg")

_SOURCE = "lakekeeper-mcp"
_DOMAIN = "lakekeeper"
_BATCH_SIZE = 500


def ingest_entities(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None = None,
    *,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int]:
    """Write canonical typed nodes and relationships through native ingestion."""
    return _native_ingest_entities(
        entities,
        relationships,
        source=_SOURCE,
        domain=_DOMAIN,
        client=client,
        graph=graph,
    )


# ── record → entity/relationship mappers ─────────────────────────────────────
def _warehouse_id(name: str) -> str:
    return f"lakekeeper:LakeWarehouse:{name}"


def _catalog_id(warehouse: str) -> str:
    return f"lakekeeper:IcebergCatalog:{warehouse}"


def _namespace_id(warehouse: str, namespace: str) -> str:
    return f"lakekeeper:IcebergNamespace:{warehouse}.{namespace}"


def _table_id(warehouse: str, namespace: str, table: str) -> str:
    return f"lakekeeper:IcebergTable:{warehouse}.{namespace}.{table}"


def _snapshot_id(warehouse: str, namespace: str, table: str, snapshot_id: Any) -> str:
    return f"lakekeeper:IcebergSnapshot:{warehouse}.{namespace}.{table}.{snapshot_id}"


def _schema_id(warehouse: str, namespace: str, table: str, schema_id: Any) -> str:
    return (
        f"lakekeeper:IcebergSchemaVersion:{warehouse}.{namespace}.{table}.{schema_id}"
    )


def map_warehouse(warehouse_record: dict[str, Any]) -> dict[str, Any]:
    """One Lakekeeper Management API warehouse record -> ``:LakeWarehouse``."""
    name = warehouse_record.get("name", "")
    storage = warehouse_record.get("storage-profile", {}) or {}
    return {
        "id": _warehouse_id(name),
        "node_type": "LakeWarehouse",
        "name": name,
        "warehouseId": warehouse_record.get("id"),
        "storageType": storage.get("type"),
        "bucket": storage.get("bucket"),
        "endpoint": storage.get("endpoint"),
        "stsEnabled": storage.get("sts-enabled"),
        "status": warehouse_record.get("status"),
        "externalToolId": str(warehouse_record.get("id") or name),
    }


def map_catalog(warehouse: str) -> dict[str, Any]:
    return {
        "id": _catalog_id(warehouse),
        "node_type": "IcebergCatalog",
        "name": f"{warehouse} catalog",
        "warehouseName": warehouse,
        "externalToolId": warehouse,
    }


def map_namespace(warehouse: str, namespace_parts: list[str]) -> dict[str, Any]:
    namespace = ".".join(namespace_parts)
    return {
        "id": _namespace_id(warehouse, namespace),
        "node_type": "IcebergNamespace",
        "name": namespace,
        "warehouseName": warehouse,
        "externalToolId": namespace,
    }


def map_table(warehouse: str, namespace: str, table_name: str) -> dict[str, Any]:
    return {
        "id": _table_id(warehouse, namespace, table_name),
        "node_type": "IcebergTable",
        "name": table_name,
        "namespace": namespace,
        "warehouseName": warehouse,
        "externalToolId": f"{namespace}.{table_name}",
    }


def map_snapshots(
    warehouse: str, namespace: str, table_name: str, snapshots: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Iceberg snapshot records -> ``:IcebergSnapshot`` entities + ``parentSnapshot`` edges."""
    entities: list[dict[str, Any]] = []
    rels: list[dict[str, Any]] = []
    for snap in snapshots or []:
        sid = snap.get("snapshot-id")
        if sid is None:
            continue
        nid = _snapshot_id(warehouse, namespace, table_name, sid)
        entities.append(
            {
                "id": nid,
                "node_type": "IcebergSnapshot",
                "name": f"snapshot {sid}",
                "snapshotId": str(sid),
                "timestampMs": snap.get("timestamp-ms"),
                "operation": (snap.get("summary") or {}).get("operation"),
                "manifestList": snap.get("manifest-list"),
                "externalToolId": str(sid),
            }
        )
        parent_id = snap.get("parent-snapshot-id")
        if parent_id is not None:
            rels.append(
                {
                    "source": nid,
                    "target": _snapshot_id(warehouse, namespace, table_name, parent_id),
                    "relationship": "parentSnapshot",
                }
            )
    return entities, rels


def map_schema_versions(
    warehouse: str, namespace: str, table_name: str, schemas: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for schema in schemas or []:
        schema_id = schema.get("schema-id")
        if schema_id is None:
            continue
        out.append(
            {
                "id": _schema_id(warehouse, namespace, table_name, schema_id),
                "node_type": "IcebergSchemaVersion",
                "name": f"schema {schema_id}",
                "schemaId": str(schema_id),
                "fieldCount": len(schema.get("fields", []) or []),
                "externalToolId": str(schema_id),
            }
        )
    return out


# ── high-level ingest entry point (Wire-First + default-on) ──────────────────
def ingest_catalog(
    warehouse: str,
    *,
    client: Any | None = None,
    graph: str | None = None,
    include_schemas: bool = True,
) -> dict[str, int]:
    """Walk one warehouse's full catalog and push it into the KG (typed + linked).

    Call sequence: list namespaces -> list tables per namespace -> get_table
    (snapshots + schemas) per table -> build entity/relationship batch ->
    ``ingest_entities`` in batches of ``_BATCH_SIZE``. Never partially commits:
    ``native_ingest.ingest_entities`` raises ``NativeIngestError`` rather than
    silently acking a partial batch.
    """
    api = get_client()

    entities: list[dict[str, Any]] = [map_catalog(warehouse)]
    relationships: list[dict[str, Any]] = []

    namespaces = api.fetch_namespaces(warehouse)
    for namespace_parts in namespaces:
        namespace = ".".join(namespace_parts)
        ns_entity = map_namespace(warehouse, namespace_parts)
        entities.append(ns_entity)
        relationships.append(
            {
                "source": _catalog_id(warehouse),
                "target": ns_entity["id"],
                "relationship": "hasNamespace",
            }
        )

        for identifier in api.fetch_tables(namespace, warehouse):
            table_name = identifier.get("name")
            if not table_name:
                continue
            table_entity = map_table(warehouse, namespace, table_name)
            entities.append(table_entity)
            relationships.append(
                {
                    "source": ns_entity["id"],
                    "target": table_entity["id"],
                    "relationship": "hasTable",
                }
            )
            relationships.append(
                {
                    "source": table_entity["id"],
                    "target": _warehouse_id(warehouse),
                    "relationship": "storedIn",
                }
            )

            table_metadata = api.fetch_table(namespace, table_name, warehouse).get(
                "metadata", {}
            )
            snap_entities, snap_rels = map_snapshots(
                warehouse, namespace, table_name, table_metadata.get("snapshots", [])
            )
            entities.extend(snap_entities)
            relationships.extend(snap_rels)
            relationships.extend(
                {
                    "source": table_entity["id"],
                    "target": snap["id"],
                    "relationship": "hasSnapshot",
                }
                for snap in snap_entities
            )

            if include_schemas:
                schema_entities = map_schema_versions(
                    warehouse, namespace, table_name, table_metadata.get("schemas", [])
                )
                entities.extend(schema_entities)
                relationships.extend(
                    {
                        "source": table_entity["id"],
                        "target": schema["id"],
                        "relationship": "hasSchemaVersion",
                    }
                    for schema in schema_entities
                )

    # Two clean phases, both batched at _BATCH_SIZE: all entities first (an
    # edge write requires both endpoints to already exist), then all
    # relationships. Simpler and correct — no straddling-batch bookkeeping.
    total_nodes = 0
    total_edges = 0
    for start in range(0, len(entities), _BATCH_SIZE):
        batch = entities[start : start + _BATCH_SIZE]
        res = ingest_entities(batch, None, client=client, graph=graph)
        total_nodes += res.get("nodes", 0)

    if relationships:
        # Redeclaring one already-written anchor entity (the catalog node)
        # alongside each relationship batch satisfies ingest_entities'
        # "at least one entity" precondition; native_ingest treats a
        # repeated entity id as idempotent, so this never double-counts.
        anchor = entities[0]
        for start in range(0, len(relationships), _BATCH_SIZE):
            batch = relationships[start : start + _BATCH_SIZE]
            res = ingest_entities([anchor], batch, client=client, graph=graph)
            total_edges += res.get("edges", 0)

    return {"nodes": total_nodes, "edges": total_edges, "warehouse": warehouse}


def register_ingest_tools(mcp: FastMCP) -> None:
    """Register the Wire-First KG catalog ingest tool."""

    @mcp.tool(
        annotations={
            "title": "Ingest Lakekeeper Catalog Into KG",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
        tags={"ingest", "mutating"},
    )
    async def lakekeeper_ingest_catalog(
        warehouse: str = Field(
            default="",
            description="Warehouse name (default from LAKEKEEPER_WAREHOUSE).",
        ),
        include_schemas: bool = Field(
            default=True,
            description="Also ingest per-table schema-version history (IcebergSchemaVersion).",
        ),
    ) -> dict[str, int]:
        """Walk one warehouse's catalog and push it into the KG as typed OWL nodes.

        Produces ``:IcebergCatalog`` -> ``:IcebergNamespace`` -> ``:IcebergTable``
        -> ``:IcebergSnapshot``/``:IcebergSchemaVersion`` chains, plus
        ``:LakeWarehouse``/``storedIn`` linkage. Never partially commits.
        """
        from agent_utilities.core.config import setting

        wh = warehouse or setting("LAKEKEEPER_WAREHOUSE", "")
        result = ingest_catalog(wh, include_schemas=include_schemas)
        return result
