"""lakekeeper-mcp: Lakekeeper (Iceberg REST catalog) API + MCP Server + A2A Server."""

from agent_connector_sdk.connector import Connector

from lakekeeper_mcp.api_client import Api
from lakekeeper_mcp.auth import get_client

connector = Connector(
    api=Api,
    get_client=get_client,
    tools="lakekeeper_mcp.mcp_server",
    instructions="Lakekeeper (Apache Iceberg REST catalog) MCP Server — namespace/table/snapshot/warehouse catalog admin, ownership classification, maintenance-request delegation (never executes expire_snapshots/compact in-process), and a Wire-First KG catalog ingest tool.",
)
