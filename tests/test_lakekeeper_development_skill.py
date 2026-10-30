"""PIPE-CONNSPEC-R133.4: the Lakekeeper development skill is packaged."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "lakekeeper_mcp" / "skills" / "lakekeeper-mcp-development" / "SKILL.md"

pytestmark = pytest.mark.spec("PIPE-CONNSPEC-R133.4")


def test_development_skill_has_rapid_contract_and_package_binding() -> None:
    text = SKILL.read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1]
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert SKILL.is_file()
    assert re.search(r"^name:\s*lakekeeper-mcp-development\s*$", frontmatter, re.M)
    assert re.search(r"^skill_type:\s*skill\s*$", frontmatter, re.M)
    assert "## Rapid delivery: the 5-minute contract" in text
    for term in (
        "lakekeeper_mcp/__init__.py",
        "lakekeeper_mcp/api_client.py",
        "lakekeeper_mcp/api/api_client_base.py",
        "lakekeeper_mcp/api/api_client_lakekeeper.py",
        "lakekeeper_mcp/auth.py",
        "lakekeeper_mcp/mcp/mcp_lakekeeper.py",
        "lakekeeper_mcp/kg_ingest.py",
        "lakekeeper_mcp/connector_sources.py",
        "LAKEKEEPER_URL",
        "LAKEKEEPER_WAREHOUSE",
        "LAKEKEEPER_SERVICE_CLIENT_ID",
        "LAKEKEEPER_SERVICE_CLIENT_SECRET",
        "LAKEKEEPER_OAUTH_SCOPE",
        "scope=lakekeeper",
        "/catalog/v1",
        "/management/v1",
        "skills/**",
        "ontology/**",
        "uv run --locked --extra test pytest",
    ):
        assert term in text

    assert "verify=False" not in text
    assert "--no-verify" not in text
    assert "pyiceberg" in text
    package_data = project["tool"]["setuptools"]["package-data"]["lakekeeper_mcp"]
    assert "skills/**" in package_data
    assert project["project"]["entry-points"]["scion_sdk.connector"] == {
        "lakekeeper-mcp": "lakekeeper_mcp:connector"
    }
