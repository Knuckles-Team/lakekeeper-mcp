# lakekeeper-mcp - AGENTS

<!-- agent-contract:start -->
## Agent contract

Tool-neutral rules for any AI agent or human working in this repository. This block is maintained by the fleet standard; edit outside the markers.

- **Owner boundary:** this repository owns one external system's calls, mappings and MCP tools (spec prefix `CONN-LAKEKEEPER-MCP-`); it depends on the connector SDK only. Feature routing across repositories: [ecosystem boundaries](https://github.com/Knuckles-Team/pipelines/blob/main/reference/ecosystem-boundaries.md).
- **Setup:** run `uv sync --locked`, then `uvx pre-commit install --hook-type pre-commit --hook-type pre-push`.
- **Gates:** `uvx pre-commit run --all-files` must pass before you push. Do not bypass hooks to get green.
- **Commits:** one logical change per commit with a `Spec: <ID>` trailer (or `Spec: none (<reason>)`), plus a `Co-Authored-By:` trailer naming the assisting agent. Stage explicit paths only; never `git add -A` or `git add .`. Use your own configured Git identity, never a tool or bot name.
- **Org rules:** [organization AGENTS.md](https://github.com/Knuckles-Team/.github/blob/main/AGENTS.md).
<!-- agent-contract:end -->

> Canonical guidance for any AI coding agent or human; tool-specific entry files
> (for example `CLAUDE.md`) only import this file. Edit this file.

## Project Structure
- `lakekeeper_mcp/`: Main server code (API client, MCP tool groups, KG ingest, skills)
- `tests/`: Test suite
- `docs/`: Architecture documentation

## Tech Stack
- Python 3.12+
- agent-connector-sdk >= 2.0.0, <3.0.0
- Model Context Protocol (MCP)
- Direct authenticated `requests` calls against Lakekeeper's Iceberg REST +
  Management APIs — **deliberately no `pyiceberg` dependency** (see
  `lakekeeper_mcp/api/api_client_lakekeeper.py`'s module docstring: `pyiceberg`
  0.11.1's base install still pins `rich<15` against the workspace's `Rich>=15`
  lock — BUG-223 — and this package's brief requires zero new heavy deps).

## Commands
- `pytest`: Run tests
- `pre-commit run --all-files`: Lint code
- `python -m agent_connector_sdk.mcp.check_env_var_drift --check`: env-var drift gate (must be 0)

## Domain notes (read before touching `auth.py` or `api_client_lakekeeper.py`)
- Lakekeeper's Iceberg REST surface is rooted at `/catalog/v1`, **not** `/v1` —
  `base_url` is the bare origin (`http://localhost:8181`), never including
  `/catalog`; the client appends both `/catalog/v1/...` and `/management/v1/...`
  itself.
- Every OAuth2 token request MUST pass `scope=lakekeeper` explicitly. The
  shared Iceberg-REST/OAuth2 client convention defaults to `scope=catalog`,
  which Lakekeeper's `lakekeeper-service` Keycloak client rejects — this is
  the single most common first-time misconfiguration
  (`services/lakekeeper/AGENTS.md`).
- Lakekeeper access tokens are short-lived (observed `expires_in=300`) —
  `auth.py`'s `_TokenCache` mints once, caches, and refreshes with a 15s skew
  margin; it never bakes a static token into a long-lived client.
- A non-JSON `2xx` response (a hibernating/misrouted backend returning HTML)
  is a hard failure in `api_client_base.py`, never an empty-list silent pass.
- This package NEVER runs `expire_snapshots`/`compact` in-process — the
  `lakekeeper_request_*` maintenance tools only name a delegation target
  (Trino/Spark's own MCPs).
- `lakekeeper_set_engine_owned` refuses to reclassify a table already marked
  `lakekeeper-native` — fail-closed, not a silent overwrite (GOC-78).

## ActionSpec / DEC-CA-07 status (as of this package's initial build, 2026-08-26)
`CA-32` (the `ActionSpec` schema extension adding `parameters`/`target_resource`/
`conflict_policy`/`requires_approval`/`approval_class`) has **not** merged onto
`agent-connector-sdk` `main` yet — confirmed by reading
`agent_connector_sdk/knowledge_graph/ontology/connector_manifest.py:274-284` (still
the three-field `{id, name, description}` shape) and the `feat/ca32-actionspec`
worktree (staged, uncommitted). This package's `connector_manifest.yml` therefore
carries only the boilerplate two-field `actions:` entries every generated
manifest gets (`epistemic-answer`, `run_graph_flow`) — the rich typed-Action
declaration for `lakekeeper_set_engine_owned` is deferred until CA-32 lands.
The tool itself is fully implemented and callable now.

## connector_manifest.yml gate status
`connector_manifest.yml` and the full capability certification bundle
(`lakekeeper_mcp/ontology/{certification.json,shapes/connector.shacl.ttl,
mappings/source.yaml,fixtures/records.json,migrations/manifest.json}`) are
generated via `agent-connector-sdk`'s real generator scripts
(`generate_connector_manifests.py` / `generate_connector_capability_bundles.py`),
same shape as every other connector in the fleet. The registration work
needed to unblock this (workspace.yml's three mirrors, four hardcoded
68->69 fleet-count constants across agent-connector-sdk, the bundle
generation itself) is done — see the `agent-connector-sdk` branch
`ca/ca-40-lakekeeper-mcp-registration` for the full accounting.

**One remaining, well-evidenced blocker**, confirmed via a direct
`check_one()` call (not inferred): `lakekeeper-mcp` has exactly ONE
violation, `"certification differs from its signed release pin"`,
because it has no entry yet in `agent_connector_sdk/knowledge_graph/
ontology.lock`. `scripts/update_ontology_lock.py` requires a trusted
release-signing public key
(`ONTOLOGY_RELEASE_SIGNING_PRIVATE_KEY_REF`, documented as
`vault://agent-connector-sdk#ONTOLOGY_RELEASE_SIGNING_PRIVATE_KEY@2` in
`docs/architecture/drift_proof_release.md`) that is not configured in
this environment; both `OPENBAO_TOKEN` and `OPENBAO_ADMIN_TOKEN`
available here return `permission denied` against
`apps/data/agent-connector-sdk`. This needs whoever holds that key's
custody to run `update_ontology_lock.py` once — a one-shot,
already-safe (atomic, no-op-on-failure) operation, not a design gap in
this package.

Separately (lower priority, does not block the release-catalog gate):
`scripts/check_connector_manifests.py --manifest connector_manifest.yml`
still reports one `[anti-sprawl]` violation because
`http://knuckles.team/kg/lakekeeper` is not yet in `agent-connector-sdk`'s
`REGISTERED_FEDERATED_IRIS` whitelist
(`agent_connector_sdk/knowledge_graph/core/ontology_federation.py`) — the
same onboarding step `jena`/`egeria` went through. Also a follow-up in
`agent-connector-sdk`, not a defect in this package's own manifest or
ontology.

## ⛔ Keep the Repository Root Pristine — No Scratch / Temp / Debug Files

**The repository ROOT must contain only canonical project files** (packaging,
config, docs, lockfiles). The only hidden directories allowed at root are
`.git/`, `.github/`, and `.specify/` (plus a local, git-ignored `.venv/`).

**NEVER write any of the following — anywhere in the repo, and ESPECIALLY at the root:**
- One-off / debug / migration scripts: `fix_*.py`, `migrate_*.py`, `refactor_*.py`,
  `replace_*.py`, `update_*.py`, `debug_*.py`, or `test_*.py` **at the root**
  (real tests live in `tests/` only).
- Databases / data dumps: `*.db`, `*.db-wal`, `*.sqlite*`, `*.corrupted`.
- Logs / command output: `*.log`, scratch `*.txt`, `*.orig`, `*.rej`, `*.bak`.
- Build artifacts: `*.tsbuildinfo`, compiled binaries, coverage files.
- AI agent scratch directories: `.agent/`, `.agents/`, `.agent_data/`, `.tmp/`,
  `.hypothesis/`, or any per-tool cache committed to git.
- Any file that is NOT production source, a test in `tests/`, documentation, or
  a recognized config/lockfile.

**Where scratch goes instead:** `~/workspace/scratch/` (experiments),
`~/workspace/reports/` (command output); tests go in `tests/` (pytest).
Before finishing a task, run `git status` and confirm no stray root files were added.

## Working Discipline — think, simplify, stay surgical, check
- **Think before coding.** State assumptions explicitly; surface options rather
  than silently picking one.
- **Simplicity first.** Minimum code that solves the stated problem.
- **Stay surgical.** Every changed line traces to the task.
- **Check against a goal.** Prove behavior with a real test or a real call
  against the live Lakekeeper deployment, not a mock alone.

## Quality Bar — Leave the Codebase Clean (REQUIRED)
Run `pre-commit run --all-files` and drive it fully green before committing.
Do not silence checks (`# noqa`, `# type: ignore`, `SKIP=`, `--no-verify`) to
force green.

## Working with Git Worktrees (multi-session)
This is a small, individually-owned package repo. Check `git worktree list`
before assuming a shared-worktree convention applies — if single-worktree,
committing on a topic branch in place is fine (confirm the branch first).

## Specs: extend first

Find the spec row that owns the behavior before any code change. Search with `git grep -n "<term>" -- specs`. Cite the row ID in the commit `Spec:` trailer. Extend the owning spec before any new spec text. Add a child row, a new rollup, or a dated `plan.md` "Amendments" entry. Create a new spec only for a capability that no spec owns. Audits, reviews, and carry-overs land in the owning spec. They never get a spec directory. Reuse an existing function, module, or store before adding one. The rules are the ecosystem [spec standard](https://github.com/Knuckles-Team/pipelines/blob/main/reference/spec-standard.md).
