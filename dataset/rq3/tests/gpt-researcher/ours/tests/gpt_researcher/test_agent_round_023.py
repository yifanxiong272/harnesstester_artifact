import logging
import types
import pytest
from gpt_researcher.agent import GPTResearcher


def _make_researcher_with_cfg(mcp_strategy_present: bool = False, value=None):
    """Create a GPTResearcher instance without calling __init__ and attach a cfg object.

    This avoids running heavy initialization and lets tests set cfg.mcp_strategy
    as needed.
    """
    inst = object.__new__(GPTResearcher)
    if mcp_strategy_present:
        inst.cfg = types.SimpleNamespace(mcp_strategy=value)
    else:
        # Provide a cfg object without mcp_strategy attribute
        inst.cfg = types.SimpleNamespace()
    return inst


def test_mcp_strategy_valid_round_023():
    r = _make_researcher_with_cfg()
    # Direct valid new-style strategies should be returned unchanged
    assert r._resolve_mcp_strategy("fast", None) == "fast"
    assert r._resolve_mcp_strategy("deep", None) == "deep"
    assert r._resolve_mcp_strategy("disabled", None) == "disabled"


def test_mcp_strategy_deprecated_optimized_round_023(caplog):
    caplog.set_level(logging.WARNING)
    r = _make_researcher_with_cfg()
    res = r._resolve_mcp_strategy("optimized", None)
    assert res == "fast"
    # The function logs a deprecation warning mentioning 'optimized'
    assert "deprecated" in caplog.text.lower()
    assert "optimized" in caplog.text


def test_mcp_strategy_deprecated_comprehensive_round_023(caplog):
    caplog.set_level(logging.WARNING)
    r = _make_researcher_with_cfg()
    res = r._resolve_mcp_strategy("comprehensive", None)
    assert res == "deep"
    assert "deprecated" in caplog.text.lower()
    assert "comprehensive" in caplog.text


def test_mcp_strategy_invalid_round_023(caplog):
    caplog.set_level(logging.WARNING)
    r = _make_researcher_with_cfg()
    # Unknown strings should log an invalid warning and default to 'fast'
    res = r._resolve_mcp_strategy("this-is-not-valid", None)
    assert res == "fast"
    assert "invalid mcp_strategy" in caplog.text.lower()


def test_mcp_max_iterations_mapping_round_023(caplog):
    caplog.set_level(logging.WARNING)
    r = _make_researcher_with_cfg()
    # Legacy numeric mapping
    assert r._resolve_mcp_strategy(None, 0) == "disabled"
    assert r._resolve_mcp_strategy(None, 1) == "fast"
    assert r._resolve_mcp_strategy(None, -1) == "deep"
    # Any other numeric value treated as fast
    assert r._resolve_mcp_strategy(None, 999) == "fast"
    # A deprecation warning about mcp_max_iterations should be emitted
    assert "deprecated" in caplog.text.lower()
    assert "mcp_max_iterations" in caplog.text


def test_config_strategy_and_default_round_023():
    # When neither parameter is provided, cfg.mcp_strategy is consulted
    r = _make_researcher_with_cfg(mcp_strategy_present=True, value="deep")
    assert r._resolve_mcp_strategy(None, None) == "deep"

    # Old-style config names are translated
    r = _make_researcher_with_cfg(mcp_strategy_present=True, value="optimized")
    assert r._resolve_mcp_strategy(None, None) == "fast"

    r = _make_researcher_with_cfg(mcp_strategy_present=True, value="comprehensive")
    assert r._resolve_mcp_strategy(None, None) == "deep"

    # If cfg exists but has no mcp_strategy attribute, default to 'fast'
    r = _make_researcher_with_cfg(mcp_strategy_present=False)
    assert r._resolve_mcp_strategy(None, None) == "fast"
