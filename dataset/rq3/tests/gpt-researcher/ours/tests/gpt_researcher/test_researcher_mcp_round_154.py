from types import SimpleNamespace
from gpt_researcher.skills.researcher import ResearchConductor


def test_instance_level_strategy_round_154():
    """Instance-level mcp_strategy present and not None should be returned."""
    dummy = SimpleNamespace()
    # Instance-level should take precedence over cfg
    dummy.researcher = SimpleNamespace(mcp_strategy='disabled', cfg=SimpleNamespace(mcp_strategy='deep'))

    result = ResearchConductor._get_mcp_strategy(dummy)

    assert result == 'disabled'


def test_cfg_level_strategy_round_154():
    """When instance-level mcp_strategy is present but None, cfg.mcp_strategy should be used."""
    dummy = SimpleNamespace()
    # Attribute exists but is None -> should fall through to cfg
    dummy.researcher = SimpleNamespace(mcp_strategy=None, cfg=SimpleNamespace(mcp_strategy='deep'))

    result = ResearchConductor._get_mcp_strategy(dummy)

    assert result == 'deep'


def test_default_strategy_round_154():
    """When neither instance-level nor cfg provide mcp_strategy, default 'fast' is returned."""
    dummy = SimpleNamespace()
    # instance-level is None and cfg has no mcp_strategy attribute
    dummy.researcher = SimpleNamespace(mcp_strategy=None, cfg=SimpleNamespace())

    result = ResearchConductor._get_mcp_strategy(dummy)

    assert result == 'fast'
