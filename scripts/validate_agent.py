#!/usr/bin/env python3
"""Validate lakekeeper-mcp end-to-end through the actual MCP tool-call path.

Unlike a script that calls the API client's Python methods directly, this
builds the real FastMCP server instance (``get_mcp_instance()``) and drives it
through ``fastmcp.Client`` over the in-memory transport — the same call path
an MCP client (Claude, the multiplexer) actually uses (tool discovery +
``call_tool``), not a shortcut around it. Requires real Lakekeeper credentials
in the environment (``LAKEKEEPER_URL``, ``LAKEKEEPER_WAREHOUSE``,
``LAKEKEEPER_SERVICE_CLIENT_SECRET``, ...) — this is a LIVE validation run,
not a mock.
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


async def main() -> int:
    try:
        from fastmcp import Client

        from lakekeeper_mcp.mcp_server import get_mcp_instance
    except ImportError as e:
        print(f"Import failed: {type(e).__name__}: {e}")
        print("Please install dependencies via `pip install .[mcp]`")
        return 1

    warehouse = os.getenv("LAKEKEEPER_WAREHOUSE", "")
    if not warehouse or not os.getenv("LAKEKEEPER_SERVICE_CLIENT_SECRET"):
        print(
            "LAKEKEEPER_WAREHOUSE / LAKEKEEPER_SERVICE_CLIENT_SECRET not set — "
            "this validation requires real credentials against a live Lakekeeper."
        )
        return 1

    print("Building lakekeeper-mcp FastMCP server instance...")
    mcp, _args, _middlewares = get_mcp_instance()

    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = sorted(t.name for t in tools)
        print(f"Discovered {len(names)} tools.")
        lakekeeper_tools = [n for n in names if n.startswith("lakekeeper_")]
        print(f"lakekeeper_* tools ({len(lakekeeper_tools)}): {lakekeeper_tools}")
        if not lakekeeper_tools:
            print("FAIL: no lakekeeper_* tools discovered")
            return 1

        print(f"\nCalling lakekeeper_list_namespaces(warehouse={warehouse!r})...")
        result = await client.call_tool(
            "lakekeeper_list_namespaces", {"warehouse": warehouse}
        )
        namespaces_payload = result.data if hasattr(result, "data") else result
        print(json.dumps(namespaces_payload, indent=2, default=str))

        namespaces = (
            namespaces_payload.get("namespaces", [])
            if isinstance(namespaces_payload, dict)
            else []
        )
        if not namespaces:
            print("No namespaces found — nothing further to validate live.")
            return 0

        namespace = ".".join(namespaces[0])
        print(f"\nCalling lakekeeper_list_tables(namespace={namespace!r})...")
        tables_result = await client.call_tool(
            "lakekeeper_list_tables", {"warehouse": warehouse, "namespace": namespace}
        )
        tables_payload = (
            tables_result.data if hasattr(tables_result, "data") else tables_result
        )
        print(json.dumps(tables_payload, indent=2, default=str))

        tables = (
            tables_payload.get("tables", []) if isinstance(tables_payload, dict) else []
        )
        if tables:
            table_name = tables[0]["name"]
            print(
                f"\nCalling lakekeeper_list_snapshots(namespace={namespace!r}, "
                f"table={table_name!r})..."
            )
            snap_result = await client.call_tool(
                "lakekeeper_list_snapshots",
                {"warehouse": warehouse, "namespace": namespace, "table": table_name},
            )
            snap_payload = (
                snap_result.data if hasattr(snap_result, "data") else snap_result
            )
            print(json.dumps(snap_payload, indent=2, default=str))

    print("\nOK: lakekeeper-mcp validated end-to-end through the MCP tool-call path.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
