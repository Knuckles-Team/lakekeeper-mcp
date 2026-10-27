"""Keep the Lakekeeper spec-delivery dashboard wired to the shared Pages job."""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _workflow():
    return yaml.safe_load((ROOT / ".github/workflows/pages.yml").read_text())


def test_pages_publishes_the_spec_dashboard_from_the_docs_tree():
    assert not (ROOT / ".github/workflows/docs.yml").exists()

    workflow = _workflow()
    publisher = workflow["jobs"]["publish-pages"]

    assert publisher["uses"] == (
        "Knuckles-Team/pipelines/.github/workflows/pages_pipeline.yml@main"
    )
    assert publisher["with"] == {
        "content_source": "docs",
        "spec_dashboard_enabled": True,
        "spec_dashboard_config": ".github/spec-dashboard.json",
    }
    assert publisher["permissions"] == {
        "contents": "read",
        "pages": "write",
        "id-token": "write",
    }

    push = workflow[True]["push"]
    assert push["branches"] == ["main"]
    assert {
        "docs/**",
        "mkdocs.yml",
        "README.md",
        "specs/**",
        ".github/spec-dashboard.json",
        ".github/workflows/pages.yml",
    } <= set(push["paths"])


def test_spec_dashboard_config_uses_the_canonical_status_source():
    config = json.loads((ROOT / ".github/spec-dashboard.json").read_text())

    assert config == {
        "version": 1,
        "sources": [{"glob": "specs/*/status.json", "kind": "spec"}],
    }
