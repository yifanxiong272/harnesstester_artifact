import pytest
from collections.abc import Mapping

from sweagent.run.common import _parse_args_to_nested_dict


def _to_plain_mapping(obj):
    """Recursively convert Mapping (including defaultdict) to plain dicts for stable comparison."""
    if isinstance(obj, Mapping):
        return {k: _to_plain_mapping(v) for k, v in obj.items()}
    return obj


def test_parse_args_with_equals_and_dot_keys_round_075():
    # --a.b=2 should create nested mapping and convert '2' to int
    # --c=hello should create top-level key with string
    args = ["--a.b=2", "--c=hello"]

    res = _parse_args_to_nested_dict(args)
    plain = _to_plain_mapping(res)

    assert isinstance(plain, dict)
    assert plain == {"a": {"b": 2}, "c": "hello"}
    # Access via chained keys as an additional assertion
    assert plain["a"]["b"] == 2


def test_parse_args_with_space_and_orphan_round_075():
    # Include a positional arg that should be skipped
    # Use --x 1 (space-separated) and --y.z two (space-separated nested)
    # End with an orphan flag --orphan which should trigger the break and not set a value
    args = ["positional", "--x", "1", "--y.z", "two", "--orphan"]

    res = _parse_args_to_nested_dict(args)
    plain = _to_plain_mapping(res)

    # The positional arg is ignored
    # x parsed and converted to int, y.z parsed as nested string
    assert "positional" not in plain
    assert plain == {"x": 1, "y": {"z": "two"}}
    # Orphan flag should not have been added
    assert "orphan" not in plain
