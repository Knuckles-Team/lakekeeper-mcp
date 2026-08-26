"""Record -> OWL entity/relationship mapping for the Lakekeeper KG ingest tool."""

from lakekeeper_mcp.kg_ingest import (
    map_catalog,
    map_namespace,
    map_schema_versions,
    map_snapshots,
    map_table,
    map_warehouse,
)


def test_map_warehouse_produces_lake_warehouse_node():
    record = {
        "id": "bf75ecf0-997e-11f1-ad91-6ff0c5e75fac",
        "name": "lakehouse",
        "status": "active",
        "storage-profile": {
            "type": "s3",
            "bucket": "lakehouse",
            "endpoint": "http://lakehouse-seaweedfs.apps.svc.cluster.local:8333/",
            "sts-enabled": False,
        },
    }
    node = map_warehouse(record)
    assert node["id"] == "lakekeeper:LakeWarehouse:lakehouse"
    assert node["node_type"] == "LakeWarehouse"
    assert node["bucket"] == "lakehouse"
    assert node["stsEnabled"] is False


def test_map_catalog_and_namespace_ids_are_stable():
    catalog = map_catalog("lakehouse")
    assert catalog["id"] == "lakekeeper:IcebergCatalog:lakehouse"

    namespace = map_namespace("lakehouse", ["analytics"])
    assert namespace["id"] == "lakekeeper:IcebergNamespace:lakehouse.analytics"
    assert namespace["node_type"] == "IcebergNamespace"


def test_map_table_id():
    table = map_table("lakehouse", "analytics", "trino_verify")
    assert table["id"] == "lakekeeper:IcebergTable:lakehouse.analytics.trino_verify"
    assert table["name"] == "trino_verify"
    assert table["namespace"] == "analytics"


def test_map_snapshots_produces_parent_snapshot_edges():
    snapshots = [
        {
            "snapshot-id": 9210639922254702422,
            "parent-snapshot-id": 1988392668464151573,
            "timestamp-ms": 1786893043608,
            "summary": {"operation": "append"},
        },
        {
            "snapshot-id": 1988392668464151573,
            "timestamp-ms": 1786893039598,
            "summary": {"operation": "append"},
        },
    ]
    entities, rels = map_snapshots("lakehouse", "analytics", "trino_verify", snapshots)

    assert len(entities) == 2
    ids = {e["id"] for e in entities}
    assert (
        "lakekeeper:IcebergSnapshot:lakehouse.analytics.trino_verify.9210639922254702422"
        in ids
    )
    assert entities[0]["operation"] == "append"

    assert len(rels) == 1
    assert rels[0]["relationship"] == "parentSnapshot"
    assert rels[0]["source"].endswith("9210639922254702422")
    assert rels[0]["target"].endswith("1988392668464151573")


def test_map_snapshots_skips_records_without_a_snapshot_id():
    entities, rels = map_snapshots(
        "lakehouse", "analytics", "t", [{"summary": {"operation": "append"}}]
    )
    assert entities == []
    assert rels == []


def test_map_schema_versions():
    schemas = [{"schema-id": 0, "fields": [{"id": 1, "name": "id", "type": "int"}]}]
    out = map_schema_versions("lakehouse", "analytics", "trino_verify", schemas)
    assert len(out) == 1
    assert out[0]["id"] == "lakekeeper:IcebergSchemaVersion:lakehouse.analytics.trino_verify.0"
    assert out[0]["fieldCount"] == 1
