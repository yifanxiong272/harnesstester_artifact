# file: sweagent/agent/agents.py:251-253
# asked: {"lines": [253], "branches": []}
# gained: {"lines": [253], "branches": []}

import pytest

def test_retry_agent_from_config_uses_model_copy_and_returns_instance():
    from sweagent.agent.agents import RetryAgent

    class FakeConfig:
        def __init__(self):
            self._called_with = None

        def model_copy(self, deep=True):
            # record the deep argument to assert it was forwarded
            self._called_with = deep
            # return something simple and immutable to compare
            return {"copied": True, "deep": deep}

    fake = FakeConfig()
    agent = RetryAgent.from_config(fake)

    # verify we got a RetryAgent instance
    assert isinstance(agent, RetryAgent)
    # verify that __init__ used model_copy(deep=True) and stored its result
    assert agent.config == {"copied": True, "deep": True}
    assert fake._called_with is True
    # verify some postconditions set by __init__
    assert agent._i_attempt == 0
    assert agent._attempt_data == []
    assert agent._agent is None

def test_retry_agent_from_config_respects_subclass_cls():
    from sweagent.agent.agents import RetryAgent

    class FakeConfig2:
        def model_copy(self, deep=True):
            return {"copied_by": "fake2", "deep": deep}

    class SubRetry(RetryAgent):
        pass

    fake = FakeConfig2()
    sub = SubRetry.from_config(fake)

    # ensure the returned object is an instance of the subclass (cls honored)
    assert isinstance(sub, SubRetry)
    # ensure config was copied and stored
    assert sub.config == {"copied_by": "fake2", "deep": True}
    # ensure initial counters are set as expected
    assert sub._i_attempt == 0
    assert sub._attempt_data == []
