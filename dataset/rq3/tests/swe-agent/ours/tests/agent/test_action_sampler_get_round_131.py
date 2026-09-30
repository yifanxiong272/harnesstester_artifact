import pytest

import sweagent.agent.action_sampler as action_sampler


class DummyBinaryTrajectoryComparison:
    def __init__(self, config, model, tools):
        # store everything so the test can assert exact argument forwarding
        self.config = config
        self.model = model
        self.tools = tools


def test_binary_trajectory_comparison_config_get_round_131(monkeypatch):
    """
    Verify that BinaryTrajectoryComparisonConfig.get forwards the provided
    config, model, and tools into the BinaryTrajectoryComparison constructor.

    This test patches the BinaryTrajectoryComparison symbol in the module to
    a dummy class that captures constructor arguments. It then calls the
    unbound get function on a synthetic config object to ensure the line
    that instantiates BinaryTrajectoryComparison is exercised and that the
    exact objects are preserved.
    """
    # Prepare sentinel objects to ensure identity preservation
    sentinel_config = object()
    sentinel_model = object()
    sentinel_tools = object()

    # Patch the class that should be constructed so we can inspect ctor args
    monkeypatch.setattr(action_sampler, "BinaryTrajectoryComparison", DummyBinaryTrajectoryComparison)

    # Call the unbound method with our sentinel config (avoids needing to construct
    # a real BaseModel instance which may require unknown fields)
    result = action_sampler.BinaryTrajectoryComparisonConfig.get(sentinel_config, sentinel_model, sentinel_tools)

    # Assertions: the patched ctor was invoked and preserved the exact objects
    assert isinstance(result, DummyBinaryTrajectoryComparison)
    assert result.config is sentinel_config
    assert result.model is sentinel_model
    assert result.tools is sentinel_tools
