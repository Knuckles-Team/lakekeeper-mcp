"""Main FastMCP server and tool registration for lakekeeper-mcp."""

import sys
from typing import Any

from agent_utilities.core.config import load_config
from agent_utilities.mcp.server_factory import create_mcp_server
from agent_utilities.mcp.verbose_tools import register_tool_surface
from fastmcp.utilities.logging import get_logger
from starlette.requests import Request
from starlette.responses import JSONResponse

from lakekeeper_mcp.api_client import Api
from lakekeeper_mcp.auth import get_client
from lakekeeper_mcp.kg_ingest import register_ingest_tools  # noqa: F401
from lakekeeper_mcp.mcp.mcp_lakekeeper import register_lakekeeper_tools  # noqa: F401

__version__ = "0.1.0"
logger = get_logger(name="lakekeeper_mcp")


def get_mcp_instance() -> tuple[Any, ...]:
    load_config()
    args, mcp, middlewares = create_mcp_server(
        name="Lakekeeper MCP",
        version=__version__,
        instructions=(
            "Lakekeeper (Apache Iceberg REST catalog) MCP Server — namespace/table/"
            "snapshot/warehouse catalog admin, ownership classification, "
            "maintenance-request delegation (never executes expire_snapshots/compact "
            "in-process), and a Wire-First KG catalog ingest tool."
        ),
    )

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(request: Request) -> JSONResponse:
        return JSONResponse({"status": "OK"})

    register_tool_surface(
        mcp,
        client_cls=Api,
        get_client=get_client,
        service="lakekeeper-mcp",
        tools_module=sys.modules[__name__],
    )

    for mw in middlewares:
        mcp.add_middleware(mw)
    return mcp, args, middlewares


def mcp_server() -> None:
    mcp, args, middlewares = get_mcp_instance()
    print(f"Lakekeeper MCP v{__version__}", file=sys.stderr)
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "streamable-http":
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    mcp_server()
