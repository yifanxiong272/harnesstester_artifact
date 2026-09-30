import pytest
from types import SimpleNamespace

# Import the class so we can call the unbound method directly
from browser_use.cli import BrowserUseApp


class DummyLog:
    def __init__(self):
        self.writes = []
        self.cleared = False

    def clear(self):
        self.cleared = True

    def write(self, msg):
        # store the exact string written for assertions
        self.writes.append(msg)


class DummyHistory:
    def __init__(self, history_list, total_seconds):
        # history_list is a list of step objects (each may have metadata attr)
        self.history = history_list
        self._total = total_seconds

    def total_duration_seconds(self):
        return self._total


def _make_self(llm=None, agent=None):
    """Create a fake `self` object compatible with BrowserUseApp.update_model_panel.

    The real method calls self.query_one(selector, RichLog) — we provide a
    query_one that accepts two args and returns a DummyLog.
    """
    dummy_log = DummyLog()

    fake_self = SimpleNamespace()
    fake_self.llm = llm
    fake_self.agent = agent

    # query_one should accept (selector, cls) per the source and return our dummy log
    def query_one(selector, cls):
        assert selector == '#model-info'
        return dummy_log

    fake_self.query_one = query_one
    return fake_self, dummy_log


def test_model_not_initialized_round_057():
    """When self.llm is falsy, the method should clear the panel and write the not-initialized message."""
    fake_self, dummy_log = _make_self(llm=None, agent=None)

    # Call the unbound method with our fake self
    BrowserUseApp.update_model_panel(fake_self)

    assert dummy_log.cleared is True, "panel should be cleared"
    # exact string from source
    assert dummy_log.writes == ['[red]Model not initialized[/]']


def test_llm_without_model_info_round_057():
    """LLM present but without model_name or model attribute should show 'Unknown' model and class name."""

    class FakeLLM:
        # no model_name nor model attribute
        temperature = None

    fake_llm = FakeLLM()

    fake_self, dummy_log = _make_self(llm=fake_llm, agent=None)

    BrowserUseApp.update_model_panel(fake_self)

    assert dummy_log.cleared is True
    # Should include class name and Unknown model
    assert any('FakeLLM' in s for s in dummy_log.writes), "class name should appear in output"
    assert any('Unknown' in s for s in dummy_log.writes), "Unknown model should be shown"
    # Should not include duration or thinking/paused indicators
    assert not any('Total Duration' in s for s in dummy_log.writes)
    assert not any('LLM is thinking' in s for s in dummy_log.writes)


def test_agent_with_model_name_running_round_057():
    """Covers branch where llm has model_name, agent has history and running=True.

    - model line includes temperature and vision when present
    - total and last-step durations are written when > 0
    - running True => 'LLM is thinking' is written
    """

    class FakeLLM:
        model_name = 'gpt-test'
        temperature = 0.7

    # last step with metadata.duration_seconds
    last_step = SimpleNamespace(metadata=SimpleNamespace(duration_seconds=1.23))
    history = DummyHistory([last_step], total_seconds=4.56)

    agent = SimpleNamespace()
    agent.settings = SimpleNamespace(use_vision=True)
    # ensure agent.state has a 'history' attribute so the hasattr check passes
    agent.state = SimpleNamespace(paused=False, history=True)
    agent.history = history
    agent.running = True

    fake_self, dummy_log = _make_self(llm=FakeLLM(), agent=agent)

    BrowserUseApp.update_model_panel(fake_self)

    # Check model line contains class name, model_name, temperature (numeric) and vision marker
    assert any('gpt-test' in s for s in dummy_log.writes)
    # temperature is rendered with degree symbol; ensure the numeric temp appears
    assert any('0.7' in s for s in dummy_log.writes)
    assert any('+ vision' in s for s in dummy_log.writes)

    # total and last-step durations should be present and formatted to 2 decimals
    assert any('Total Duration' in s and '4.56s' in s for s in dummy_log.writes)
    assert any('Last Step Duration' in s and '1.23s' in s for s in dummy_log.writes)

    # running True should produce the 'thinking' message
    assert any('LLM is thinking' in s for s in dummy_log.writes)


def test_agent_with_model_attr_paused_round_057():
    """Covers model attribute branch and paused state when durations are zero.

    - llm.model should be used when model_name absent
    - temperature falsy => no temp string
    - total duration == 0 => no duration writes
    - running False and state.paused True => show paused message
    """

    class FakeLLM:
        model = 'model-attr'
        temperature = 0  # falsy; should produce empty temp_str

    # last step exists but metadata is None -> step_duration should fall back to 0
    last_step = SimpleNamespace(metadata=None)
    history = DummyHistory([last_step], total_seconds=0.0)

    agent = SimpleNamespace()
    agent.settings = SimpleNamespace(use_vision=False)
    # ensure agent.state has a 'history' attribute so the hasattr check passes
    agent.state = SimpleNamespace(paused=True, history=True)
    agent.history = history
    agent.running = False

    fake_self, dummy_log = _make_self(llm=FakeLLM(), agent=agent)

    BrowserUseApp.update_model_panel(fake_self)

    # Model line should include the model attribute value
    assert any('model-attr' in s for s in dummy_log.writes)
    # No total/last-step durations when total duration is zero
    assert not any('Total Duration' in s for s in dummy_log.writes)
    assert not any('Last Step Duration' in s for s in dummy_log.writes)
    # Paused message should be present
    assert any('LLM paused' in s for s in dummy_log.writes)
