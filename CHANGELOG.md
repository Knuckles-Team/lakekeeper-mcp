# Changelog

All notable changes to `lakekeeper-mcp` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.7] - 2026-10-30

### Changed
- Require `scion-sdk>=0.6.4,<0.7.0`; `uv.lock` relocked.

## [0.3.5] - 2026-10-26

### Added
- Add the packaged Lakekeeper connector development skill and delivery contract.

## [0.3.4] - 2026-10-24

### Changed
- Central connector migration: requires `agent-connector-sdk>=0.5.4`; server bootstrap, version, containers, ontology artifacts, security scaffold and pre-commit config are provided centrally.

## [Unreleased]
### Surface backfill (scion-sdk 0.9.0)
- Removed the duplicate raw `lakekeeper_fetch_*` and `lakekeeper_get_config` tools (the curated `list_*`/`get_*`/`config` tools remain) and the always-failing `lakekeeper_cloudevents_subscribe` placeholder.
- Declared a data resource, tool-use contracts, links, data locations, business roles, an operator prompt and two business-role prompts; raised `scion-sdk` to `>=0.9.0`.


## [0.1.0] - 2026-08-26

### Added
- Initial release: MCP server, A2A agent, and API client for Lakekeeper
  (Apache Iceberg REST catalog) integration — namespaces, tables, snapshots,
  schema versions, warehouses, and table ownership classification.
- Connector capability certification bundle (`connector_manifest.yml`,
  ontology, KG ingestion).
- Standard fleet scaffolding (CI workflows, pre-commit, docs site, packaging
  metadata) to bring the repo to parity with the rest of the agent-packages
  fleet.
