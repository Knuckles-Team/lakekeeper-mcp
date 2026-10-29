"""Keep the Lakekeeper spec-delivery dashboard wired to the shared Pages job."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pages_publishes_the_spec_dashboard_from_the_docs_tree():
    assert not (ROOT / ".github/workflows/docs.yml").exists()


def test_spec_dashboard_config_uses_the_canonical_status_source():
    config = json.loads((ROOT / ".github/spec-dashboard.json").read_text())

    assert config == {
        "version": 1,
        "sources": [{"glob": "specs/*/status.json", "kind": "spec"}],
    }
