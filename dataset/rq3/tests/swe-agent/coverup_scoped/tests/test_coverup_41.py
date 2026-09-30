# file: sweagent/agent/agents.py:829-864
# asked: {"lines": [850, 851, 852, 861], "branches": [[860, 861]]}
# gained: {"lines": [850, 851, 852, 861], "branches": [[860, 861]]}

import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace

from sweagent.agent.agents import DefaultAgent
from sweagent.types import StepOutput

class DummyTools:
    def __init__(self, flag: bool):
        # mimic expected attribute
        self.config = SimpleNamespace(parse_function=None)
        self._flag = flag

    def check_for_submission_cmd(self, observation):
        return self._flag

class EnvRaises:
    def read_file(self, path, encoding=None, errors=None):
        raise ValueError("boom")

class EnvReturns:
    def __init__(self, content: str):
        self.content = content
    def read_file(self, path, encoding=None, errors=None):
        # mimic SWEEnv.read_file signature
        return self.content

def make_agent(tools):
    # minimal args for DefaultAgent; types are not strictly enforced at runtime here
    return DefaultAgent(templates=object(), tools=tools, history_processors=[], model=object())

def test_handle_submission_readfile_other_exception(monkeypatch):
    tools = DummyTools(True)
    agent = make_agent(tools)
    # set env that raises a non-FileNotFoundError exception
    agent._env = EnvRaises()

    # replace logger.exception to capture calls and avoid noisy logging
    agent.logger.exception = MagicMock()
    agent.logger.warning = MagicMock()

    step = StepOutput(observation="original-observation", exit_status=None, submission=None, done=False)
    result = agent.handle_submission(step)

    # Should have caught the generic exception and returned the (copied) step unchanged
    assert isinstance(result, StepOutput)
    assert result.submission is None
    assert result.observation == "original-observation"
    assert result.done is False
    assert result.exit_status is None

    # logger.exception should have been called with an exception message
    assert agent.logger.exception.called
    # ensure warning not called in this path (that's for FileNotFoundError)
    agent.logger.warning.assert_not_called()

def test_handle_submission_with_existing_exit_status_updates(monkeypatch):
    tools = DummyTools(True)
    agent = make_agent(tools)
    # env returns a non-empty submission
    content = "some patch content\n"
    agent._env = EnvReturns(content)

    # mock loggers to avoid noisy logs
    agent.logger.info = MagicMock()
    agent.logger.exception = MagicMock()
    agent.logger.warning = MagicMock()

    # Create a step that already has an exit_status to trigger the 'elif step.submission' branch
    step = StepOutput(observation="orig", exit_status="previous", submission=None, done=False)
    result = agent.handle_submission(step)

    # After handling, submission and observation should be set to the content, done True,
    # and exit_status updated to include the previous status
    assert result.submission == content
    assert result.observation == content
    assert result.done is True
    assert result.exit_status == f"submitted (previous)"

    # logger.info should have been called indicating a found submission
    assert agent.logger.info.called
