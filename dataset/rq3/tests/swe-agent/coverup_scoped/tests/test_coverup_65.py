# file: sweagent/agent/action_sampler.py:154-156
# asked: {"lines": [155, 156], "branches": []}
# gained: {"lines": [155, 156], "branches": []}

import pytest

def test_binary_trajectory_comparison_init_sets_attributes(monkeypatch):
    import importlib
    import sweagent.agent.action_sampler as action_sampler_mod

    # Prepare a dummy logger to avoid side effects from real logger configuration
    class DummyLogger:
        def debug(self, *a, **k): pass
        def info(self, *a, **k): pass
        def warning(self, *a, **k): pass
        def error(self, *a, **k): pass

    # Ensure the module that provides get_logger returns our DummyLogger when reloaded
    monkeypatch.setattr('sweagent.utils.log.get_logger', lambda *args, **kwargs: DummyLogger(), raising=True)

    # Reload the action_sampler module so AbstractActionSampler picks up the patched get_logger
    importlib.reload(action_sampler_mod)
    BinaryTrajectoryComparison = action_sampler_mod.BinaryTrajectoryComparison
    BinaryTrajectoryComparisonConfig = action_sampler_mod.BinaryTrajectoryComparisonConfig

    dummy_model = object()
    dummy_tools = object()
    config = BinaryTrajectoryComparisonConfig()

    sampler = BinaryTrajectoryComparison(config, dummy_model, dummy_tools)

    # Verify assignment from AbstractActionSampler.__init__ and BinaryTrajectoryComparison.__init__
    assert sampler._model is dummy_model
    assert sampler._tools is dummy_tools
    assert sampler.config is config
    # Ensure a logger attribute exists (we don't depend on exact type to avoid fragile coupling)
    assert hasattr(sampler, "_logger")
    assert sampler._logger is not None

def test_binary_trajectory_comparison_init_with_custom_config_and_objects(monkeypatch):
    import importlib
    import sweagent.agent.action_sampler as action_sampler_mod

    class DummyLogger:
        def debug(self, *a, **k): pass
        def info(self, *a, **k): pass
        def warning(self, *a, **k): pass
        def error(self, *a, **k): pass

    monkeypatch.setattr('sweagent.utils.log.get_logger', lambda *args, **kwargs: DummyLogger(), raising=True)
    importlib.reload(action_sampler_mod)
    BinaryTrajectoryComparison = action_sampler_mod.BinaryTrajectoryComparison
    BinaryTrajectoryComparisonConfig = action_sampler_mod.BinaryTrajectoryComparisonConfig

    config = BinaryTrajectoryComparisonConfig(min_n_samples=5, max_n_samples=6, system_template="sys", instance_template="inst", comparison_template="comp")

    class FakeModel:
        def __init__(self):
            self.called = False
        def reset_stats(self):
            self.called = True
    fake_model = FakeModel()
    fake_tools = {"tool": "value"}

    sampler = BinaryTrajectoryComparison(config, fake_model, fake_tools)

    assert sampler._model is fake_model
    assert sampler._tools is fake_tools
    assert sampler.config is config
    assert sampler.config.min_n_samples == 5
    assert sampler.config.max_n_samples == 6
    assert sampler.config.system_template == "sys"
    assert sampler.config.instance_template == "inst"
    assert sampler.config.comparison_template == "comp"
    # Ensure logger exists and is usable
    assert hasattr(sampler, "_logger")
    assert callable(getattr(sampler._logger, "info", None))
