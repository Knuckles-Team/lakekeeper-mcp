"""Import-time smoke test — every module in the package must import cleanly."""


def test_startup():
    import lakekeeper_mcp.api_client  # noqa: F401
    import lakekeeper_mcp.auth  # noqa: F401
    import lakekeeper_mcp.kg_ingest  # noqa: F401
    import lakekeeper_mcp.mcp.mcp_lakekeeper  # noqa: F401
    import lakekeeper_mcp.mcp_server  # noqa: F401
    import lakekeeper_mcp.models  # noqa: F401
