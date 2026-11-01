# CONN-LAKEKEEPER-MCP-CONNECTOR-CONTENT — Requirements

Governing spec: [spec.md](spec.md).

Each row is one requirement. A row names the file it touches and the test that proves it. The generator sets each row's state in `status.json`.

| ID | Requirement | Acceptance |
|---|---|---|
| `CONN-LAKEKEEPER-MCP-CONNECTOR-CONTENT-R001` | **Default content.** `pyproject.toml` declares `lakekeeper-mcp` as the single `scion_sdk.connector` entry point. The server lists the packaged `skill://` and `ontology://` resources and the packaged prompts with no `content=` argument. Proving test: `tests/test_default_content_surfaces.py`. Caller chain: the `lakekeeper-mcp` console script (`scion_sdk.cli:serve`) loads the `scion_sdk.connector` entry point `lakekeeper_mcp:connector` (`lakekeeper_mcp/__init__.py:8`), which the SDK `build_server` turns into the served MCP server and its resources and prompts. Shape: `connector = Connector(...)` in `lakekeeper_mcp/__init__.py:8` passes no `content=`, so the SDK reuses `ConnectorContent.for_package` over the packaged `lakekeeper_mcp/skills` and `lakekeeper_mcp/ontology` folders and any packaged prompts. | `resources/list` includes `skill://` and `ontology://`; `prompts/list` includes each packaged prompt. Planned test: `tests/test_default_content_surfaces.py::test_default_content_surfaces`. |
