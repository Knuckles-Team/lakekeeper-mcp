"""GOC-78 single-writer ownership classification: default + fail-closed rejection."""

import pytest

from lakekeeper_mcp.api.api_client_base import LakekeeperApiError
from lakekeeper_mcp.mcp.mcp_lakekeeper import (
    _OWNERSHIP_PROPERTY,
    _ownership_of,
    _reject_if_reclassifying_native,
)


def test_default_ownership_is_lakekeeper_native_when_unclassified():
    assert _ownership_of({}) == "lakekeeper-native"
    assert _ownership_of({"properties": {}}) == "lakekeeper-native"


def test_ownership_reads_explicit_classification():
    metadata = {"properties": {_OWNERSHIP_PROPERTY: "engine"}}
    assert _ownership_of(metadata) == "engine"


def test_ownership_reads_explicit_lakekeeper_native_classification():
    metadata = {"properties": {_OWNERSHIP_PROPERTY: "lakekeeper-native"}}
    assert _ownership_of(metadata) == "lakekeeper-native"


def test_reclassifying_away_from_native_is_rejected():
    """The negative test this lane's contract names explicitly."""
    with pytest.raises(LakekeeperApiError, match="lakekeeper-native"):
        _reject_if_reclassifying_native("lakekeeper-native", "engine")


def test_reclassifying_native_to_native_is_allowed():
    _reject_if_reclassifying_native(
        "lakekeeper-native", "lakekeeper-native"
    )  # no raise


def test_classifying_unclassified_table_as_engine_is_rejected_by_the_safe_default():
    """An absent classification reads as 'lakekeeper-native' (safe default,

    ``_ownership_of``), so classifying a never-explicitly-set table as
    'engine' hits the same fail-closed guard as an explicit prior write —
    the guard applies uniformly to the default, not only to an explicit one.
    """
    with pytest.raises(LakekeeperApiError):
        _reject_if_reclassifying_native(_ownership_of({}), "engine")


def test_classifying_engine_table_is_allowed():
    _reject_if_reclassifying_native("engine", "lakekeeper-native")  # no raise
    _reject_if_reclassifying_native("engine", "engine")  # no raise
