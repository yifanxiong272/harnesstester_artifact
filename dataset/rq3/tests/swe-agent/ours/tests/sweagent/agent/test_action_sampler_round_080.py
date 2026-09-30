import pytest
from sweagent.agent import action_sampler
from sweagent.agent.action_sampler import AbstractActionSampler


class DummyModel:
    pass


class DummyTools:
    pass


def test_init_and_super_get_action_round_080(monkeypatch):
    # Patch the module-level get_logger used by AbstractActionSampler.__init__ to avoid side effects
    monkeypatch.setattr(action_sampler, "get_logger", lambda *a, **k: "dummy_logger")

    model = DummyModel()
    tools = DummyTools()

    class ConcreteSampler(AbstractActionSampler):
        def get_action(self, problem_statement, trajectory, history):
            # Call the base implementation to execute the `pass` in AbstractActionSampler.get_action
            super().get_action(problem_statement, trajectory, history)
            return {"ok": True, "ps": problem_statement, "traj": trajectory, "hist_len": len(history)}

    sampler = ConcreteSampler(model, tools)

    # Verify constructor assigned attributes correctly
    assert sampler._model is model
    assert sampler._tools is tools
    # Our patched get_logger should have been used
    assert sampler._logger == "dummy_logger"

    # Call get_action and assert the ConcreteSampler behavior; calling super() exercised the base `pass` line
    out = sampler.get_action("problem", [1, 2, 3], [{"a": 1}])
    assert out == {"ok": True, "ps": "problem", "traj": [1, 2, 3], "hist_len": 1}


def test_cannot_instantiate_abstract_round_080():
    # AbstractActionSampler is abstract; attempting to instantiate it should raise a TypeError
    with pytest.raises(TypeError):
        AbstractActionSampler(None, None)
