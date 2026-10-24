"""Main FastMCP server and tool registration for lakekeeper-mcp."""

from lakekeeper_mcp.kg_ingest import register_ingest_tools  # noqa: F401
from lakekeeper_mcp.mcp.mcp_lakekeeper import register_lakekeeper_tools  # noqa: F401

# SDK discovery registers the register_<tag>_tools functions bound in this module.
__all__ = ["register_ingest_tools", "register_lakekeeper_tools"]
