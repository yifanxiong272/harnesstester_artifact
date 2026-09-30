import logging
import pytest
from gpt_researcher.agent import GPTResearcher


def _make_researcher_with_cfg(cfg):
    # Create instance without calling __init__ to avoid heavy initialization
    inst = object.__new__(GPTResearcher)
    inst.cfg = cfg
    return inst


def test_resolve_mcp_strategy_param_known_round_023():
    """Known new strategy names should be returned unchanged."""
    r = _make_researcher_with_cfg(object())

    assert r._resolve_mcp_strategy("fast", None) == "fast"
    assert r._resolve_mcp_strategy("deep", None) == "deep"
    assert r._resolve_mcp_strategy("disabled", None) == "disabled"


def test_resolve_mcp_strategy_param_deprecated_and_invalid_round_023(caplog):
    """Deprecated old names map to new ones and invalid names default to 'fast', warnings emitted."""
    caplog.set_level(logging.WARNING)
    r = _make_researcher_with_cfg(object())

    caplog.clear()
    res_opt = r._resolve_mcp_strategy("optimized", None)
    assert res_opt == "fast"
    # Expect a deprecation message about optimized -> fast
    assert any("deprecated" in rec.getMessage() and "optimized" in rec.getMessage() for rec in caplog.records)

    caplog.clear()
    res_comp = r._resolve_mcp_strategy("comprehensive", None)
    assert res_comp == "deep"
    # Expect a deprecation message about comprehensive -> deep
    assert any("deprecated" in rec.getMessage() and "comprehensive" in rec.getMessage() for rec in caplog.records)

    caplog.clear()
    res_invalid = r._resolve_mcp_strategy("totally-invalid-strat", None)
    assert res_invalid == "fast"
    # Expect a warning mentioning invalid mcp_strategy
    assert any("Invalid mcp_strategy" in rec.getMessage() for rec in caplog.records)


def test_resolve_mcp_strategy_max_iterations_round_023(caplog):
    """Legacy mcp_max_iterations values convert to expected strategies and produce a deprecation warning."""
    caplog.set_level(logging.WARNING)
    r = _make_researcher_with_cfg(object())

    caplog.clear()
    assert r._resolve_mcp_strategy(None, 0) == "disabled"
    assert r._resolve_mcp_strategy(None, 1) == "fast"
    assert r._resolve_mcp_strategy(None, -1) == "deep"
    assert r._resolve_mcp_strategy(None, 5) == "fast"

    # The first call entering the mcp_max_iterations branch logs the deprecation
    assert any("mcp_max_iterations is deprecated" in rec.getMessage() for rec in caplog.records)


def test_resolve_mcp_strategy_config_round_023():
    """When parameters are None, the cfg.mcp_strategy is used with backwards compatibility and defaults to fast."""
    class C:
        pass

    # New-style config names
    c1 = C()
    c1.mcp_strategy = "deep"
    r1 = _make_researcher_with_cfg(c1)
    assert r1._resolve_mcp_strategy(None, None) == "deep"

    # Old optimized -> fast
    c2 = C()
    c2.mcp_strategy = "optimized"
    r2 = _make_researcher_with_cfg(c2)
    assert r2._resolve_mcp_strategy(None, None) == "fast"

    # Old comprehensive -> deep
    c3 = C()
    c3.mcp_strategy = "comprehensive"
    r3 = _make_researcher_with_cfg(c3)
    assert r3._resolve_mcp_strategy(None, None) == "deep"

    # No cfg.mcp_strategy attribute -> default to fast
    r4 = _make_researcher_with_cfg(object())
    assert r4._resolve_mcp_strategy(None, None) == "fast"
