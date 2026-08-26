"""Lakekeeper (Apache Iceberg REST catalog) API client.

Talks directly to Lakekeeper's REST surfaces over ``requests`` — the Iceberg REST
Catalog spec (``/catalog/v1/...``) and Lakekeeper's own Management API
(``/management/v1/...``) — rather than depending on the ``pyiceberg`` SDK.

**Deliberate deviation from the lane file's original PyIceberg-based design,
recorded here rather than silently substituted:** ``pyiceberg`` 0.11.1 (latest,
confirmed live against PyPI) still pins ``rich<15.0.0,>=10.11.0`` even in its
dependency-free base install (no ``pyarrow`` extra pulled in), which directly
conflicts with the workspace's ``Rich>=15`` lock (BUG-223) and would either
break the shared resolution or force an isolated venv fork purely to carry one
dependency. Combined with this lane's explicit "no new heavy dependencies"
requirement, a thin authenticated REST client (the same shape every other
fleet package in this repo uses — see ``jena_mcp.api.api_client_base``) is the
lower-risk, template-conformant choice for a catalog CONTROL PLANE wrapper
(namespace/table/snapshot/warehouse admin) that never needs Arrow-native data
reads — those happen through Trino/Spark's own MCPs, never here (this
package's explicit non-goal).

Every method here has been proven against the live cluster catalog
(``http://lakekeeper.arpa/catalog``, warehouse ``lakehouse``, namespace
``analytics``, table ``trino_verify`` — the exact table Trino/Spark's sibling
lanes CA-52/CA-53 wrote and read) — see the package's own evidence file.
"""

from __future__ import annotations

from typing import Any

from lakekeeper_mcp.api.api_client_base import ApiClientBase, LakekeeperApiError

__all__ = ["LakekeeperApi", "LakekeeperApiError"]


class LakekeeperApi(ApiClientBase):
    """Authenticated Lakekeeper REST + Management API client.

    ``base_url`` is the bare Lakekeeper origin (e.g. ``http://lakekeeper.arpa``,
    NOT including ``/catalog``) — this client appends ``/catalog/v1/...`` and
    ``/management/v1/...`` itself, matching the two distinct API roots
    Lakekeeper actually serves (confirmed live: ``/catalog/v1/config`` is the
    Iceberg REST root; ``/v1/config`` and ``/iceberg/v1/config`` both 404).
    """

    def __init__(self, *args: Any, default_warehouse: str = "", **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.default_warehouse = default_warehouse
        self._prefix_cache: dict[str, str] = {}

    # ── catalog discovery ────────────────────────────────────────────────
    def get_config(self, warehouse: str = "") -> dict[str, Any]:
        """Iceberg REST catalog discovery for one warehouse.

        Returns Lakekeeper's ``{"overrides": {...}, "defaults": {...}}`` config
        payload; ``defaults.prefix`` is the warehouse UUID every subsequent
        catalog call must address (Lakekeeper multiplexes many warehouses
        behind one Iceberg REST root by ``{prefix}``).
        """
        wh = warehouse or self.default_warehouse
        params = {"warehouse": wh} if wh else None
        return self.request("GET", "/catalog/v1/config", params=params)

    def _resolve_prefix(self, warehouse: str = "") -> str:
        wh = warehouse or self.default_warehouse
        if not wh:
            raise LakekeeperApiError(
                "a Lakekeeper warehouse name must be configured "
                "(LAKEKEEPER_WAREHOUSE) or passed explicitly"
            )
        if wh not in self._prefix_cache:
            config = self.get_config(wh)
            prefix = (config.get("defaults") or {}).get("prefix")
            if not prefix:
                raise LakekeeperApiError(
                    f"Lakekeeper /catalog/v1/config for warehouse {wh!r} returned no "
                    "'defaults.prefix'"
                )
            self._prefix_cache[wh] = str(prefix)
        return self._prefix_cache[wh]

    # ── catalog: namespaces ──────────────────────────────────────────────
    def fetch_namespaces(self, warehouse: str = "", parent: str = "") -> list[list[str]]:
        prefix = self._resolve_prefix(warehouse)
        params = {"parent": parent} if parent else None
        result = self.request(
            "GET", f"/catalog/v1/{prefix}/namespaces", params=params
        )
        return result.get("namespaces", [])

    def fetch_namespace(self, namespace: str, warehouse: str = "") -> dict[str, Any]:
        prefix = self._resolve_prefix(warehouse)
        return self.request("GET", f"/catalog/v1/{prefix}/namespaces/{namespace}")

    # ── catalog: tables ──────────────────────────────────────────────────
    def fetch_tables(self, namespace: str, warehouse: str = "") -> list[dict[str, Any]]:
        prefix = self._resolve_prefix(warehouse)
        result = self.request(
            "GET", f"/catalog/v1/{prefix}/namespaces/{namespace}/tables"
        )
        return result.get("identifiers", [])

    def fetch_table(
        self, namespace: str, table: str, warehouse: str = ""
    ) -> dict[str, Any]:
        """Full table load response, including ``metadata.snapshots`` and
        ``metadata.schemas`` — the single call this client's snapshot/schema
        readers both key off, matching how Lakekeeper's REST surface actually
        returns table state (there is no separate ``/snapshots`` endpoint)."""
        prefix = self._resolve_prefix(warehouse)
        return self.request(
            "GET", f"/catalog/v1/{prefix}/namespaces/{namespace}/tables/{table}"
        )

    def fetch_snapshots(
        self, namespace: str, table: str, warehouse: str = ""
    ) -> list[dict[str, Any]]:
        """Snapshot history for one table.

        Raises :class:`LakekeeperApiError` (via ``get_table``'s 404 handling)
        for a nonexistent table — never returns ``[]`` for that case, so a
        caller can distinguish "table not found" from "table has no
        snapshots yet" (this lane's acceptance gate 3's known-bad case).
        """
        metadata = self.fetch_table(namespace, table, warehouse).get("metadata", {})
        return metadata.get("snapshots", [])

    def fetch_schema_versions(
        self, namespace: str, table: str, warehouse: str = ""
    ) -> list[dict[str, Any]]:
        metadata = self.fetch_table(namespace, table, warehouse).get("metadata", {})
        return metadata.get("schemas", [])

    # ── management: warehouses ───────────────────────────────────────────
    def fetch_warehouses(self, project_id: str = "") -> list[dict[str, Any]]:
        params = {"projectId": project_id} if project_id else None
        result = self.request(
            "GET", "/management/v1/warehouse", params=params
        )
        return result.get("warehouses", [])

    def fetch_warehouse(self, warehouse_id: str) -> dict[str, Any]:
        return self.request("GET", f"/management/v1/warehouse/{warehouse_id}")

    def get_warehouse_storage_profile(self, warehouse_id: str) -> dict[str, Any]:
        return self.fetch_warehouse(warehouse_id).get("storage-profile", {})

    # ── management: server/bootstrap status (read-only) ─────────────────
    def get_server_info(self) -> dict[str, Any]:
        return self.request("GET", "/management/v1/info")
