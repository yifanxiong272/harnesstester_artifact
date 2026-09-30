# file: gpt_researcher/agent.py:216-280
# asked: {"lines": [236, 237, 239, 240, 241, 242, 243, 244, 245, 246, 248, 249, 250, 254, 255, 257, 258, 259, 260, 261, 262, 265, 274, 275, 276, 277, 280], "branches": [[234, 236], [236, 237], [236, 239], [239, 240], [239, 243], [243, 244], [243, 248], [253, 254], [257, 258], [257, 259], [259, 260], [259, 261], [261, 262], [261, 265], [268, 280], [271, 274], [274, 275], [274, 276], [276, 277], [276, 280]]}
# gained: {"lines": [236, 237, 239, 240, 241, 242, 243, 244, 245, 246, 248, 249, 250, 254, 255, 257, 258, 259, 260, 261, 262, 265, 274, 275, 276, 277, 280], "branches": [[234, 236], [236, 237], [236, 239], [239, 240], [239, 243], [243, 244], [243, 248], [253, 254], [257, 258], [257, 259], [259, 260], [259, 261], [261, 262], [261, 265], [268, 280], [271, 274], [274, 275], [274, 276], [276, 277]]}

import logging
from types import SimpleNamespace

import pytest

from gpt_researcher.agent import GPTResearcher


def make_researcher():
    # Create instance without running __init__ to avoid side effects
    r = GPTResearcher.__new__(GPTResearcher)
    # Ensure cfg exists for tests that need it (may be replaced per-test)
    r.cfg = SimpleNamespace()
    return r


def test_mcp_strategy_variants_and_warnings(caplog):
    r = make_researcher()

    # Valid new-style strategies should be returned unchanged
    assert r._resolve_mcp_strategy("fast", None) == "fast"
    assert r._resolve_mcp_strategy("deep", None) == "deep"
    assert r._resolve_mcp_strategy("disabled", None) == "disabled"

    # Deprecated 'optimized' should return 'fast' and emit a deprecation warning
    caplog.set_level(logging.WARNING)
    caplog.clear()
    res = r._resolve_mcp_strategy("optimized", None)
    assert res == "fast"
    # ensure a deprecation warning was emitted
    assert any("deprecated" in record.getMessage() for record in caplog.records)

    # Deprecated 'comprehensive' should return 'deep' and emit a deprecation warning
    caplog.clear()
    res = r._resolve_mcp_strategy("comprehensive", None)
    assert res == "deep"
    assert any("deprecated" in record.getMessage() for record in caplog.records)

    # Invalid strategy string should return 'fast' and emit a warning mentioning 'Invalid'
    caplog.clear()
    res = r._resolve_mcp_strategy("not-a-strategy", None)
    assert res == "fast"
    assert any("Invalid mcp_strategy" in record.getMessage() for record in caplog.records)


@pytest.mark.parametrize("val,expected", [
    (0, "disabled"),
    (1, "fast"),
    (-1, "deep"),
    (5, "fast"),  # any other number treated as 'fast'
])
def test_mcp_max_iterations_deprecated_mapping(caplog, val, expected):
    r = make_researcher()
    # mcp_max_iterations path should emit a deprecation warning
    caplog.set_level(logging.WARNING)
    caplog.clear()
    res = r._resolve_mcp_strategy(None, val)
    assert res == expected
    assert any("mcp_max_iterations is deprecated" in record.getMessage() for record in caplog.records)


def test_config_strategy_legacy_and_default():
    r = make_researcher()

    # Legacy config 'optimized' should map to 'fast'
    r.cfg = SimpleNamespace(mcp_strategy="optimized")
    assert r._resolve_mcp_strategy(None, None) == "fast"

    # Legacy config 'comprehensive' should map to 'deep'
    r.cfg = SimpleNamespace(mcp_strategy="comprehensive")
    assert r._resolve_mcp_strategy(None, None) == "deep"

    # If cfg has no mcp_strategy attribute, default to 'fast'
    r.cfg = SimpleNamespace()  # no attribute
    assert r._resolve_mcp_strategy(None, None) == "fast"
