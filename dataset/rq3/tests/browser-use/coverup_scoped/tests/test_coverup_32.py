# file: browser_use/cli.py:1322-1373
# asked: {"lines": [1322, 1324, 1325, 1327, 1329, 1330, 1331, 1332, 1333, 1336, 1337, 1338, 1339, 1340, 1343, 1346, 1348, 1351, 1352, 1353, 1354, 1356, 1359, 1360, 1361, 1364, 1367, 1368, 1369, 1370, 1371, 1373], "branches": [[1327, 1329], [1327, 1373], [1330, 1331], [1330, 1332], [1332, 1333], [1332, 1336], [1336, 1337], [1336, 1343], [1346, 0], [1346, 1348], [1351, 1352], [1351, 1359], [1353, 1354], [1353, 1356], [1360, 1361], [1360, 1367], [1367, 0], [1367, 1368], [1368, 1369], [1368, 1370], [1370, 0], [1370, 1371]]}
# gained: {"lines": [1322, 1324, 1325, 1327, 1329, 1330, 1331, 1332, 1333, 1336, 1337, 1338, 1339, 1340, 1343, 1346, 1348, 1351, 1352, 1353, 1354, 1359, 1360, 1361, 1364, 1367, 1368, 1369, 1370, 1371, 1373], "branches": [[1327, 1329], [1327, 1373], [1330, 1331], [1330, 1332], [1332, 1333], [1336, 1337], [1336, 1343], [1346, 0], [1346, 1348], [1351, 1352], [1351, 1359], [1353, 1354], [1360, 1361], [1360, 1367], [1367, 1368], [1368, 1369], [1368, 1370], [1370, 1371]]}

import types
import pytest

from browser_use.cli import BrowserUseApp


class FakeRichLog:
    def __init__(self):
        self.messages = []
        self.cleared = False

    def clear(self):
        self.cleared = True

    def write(self, msg: str):
        self.messages.append(msg)


class SimpleMetadata:
    def __init__(self, duration_seconds):
        self.duration_seconds = duration_seconds


class HistoryStep:
    def __init__(self, metadata):
        self.metadata = metadata


class FakeHistory:
    def __init__(self, steps, total_duration):
        # steps: list of HistoryStep
        self.history = steps
        self._total = total_duration

    def total_duration_seconds(self):
        return self._total


class FakeSettings:
    def __init__(self, use_vision=False):
        self.use_vision = use_vision


class FakeAgent:
    def __init__(self):
        # populate with attributes as tests need
        self.settings = FakeSettings(False)
        self.state = types.SimpleNamespace()  # will be assigned attributes by tests
        self.history = None
        self.running = False


class FakeLLM:
    def __init__(self, model_name=None, model=None, temperature=None):
        if model_name is not None:
            self.model_name = model_name
        if model is not None:
            self.model = model
        self.temperature = temperature


def setup_app_with_log():
    """Helper to create an app instance and a fresh FakeRichLog, and monkeypatch query_one on the instance."""
    app = BrowserUseApp({})  # pass required config argument
    fake_log = FakeRichLog()
    # Monkeypatch query_one on the instance to return our fake log regardless of args
    app.query_one = lambda selector, cls=None: fake_log
    return app, fake_log


def test_model_not_initialized():
    app, fake_log = setup_app_with_log()
    # Ensure llm is None
    app.llm = None
    # Run
    app.update_model_panel()
    # Assertions
    assert fake_log.cleared is True
    assert fake_log.messages == ['[red]Model not initialized[/]']


def test_llm_without_agent_uses_model_attr_and_model_name_precedence():
    app, fake_log = setup_app_with_log()
    # Case 1: llm has model_name attribute and no agent -> should use model_name
    app.llm = FakeLLM(model_name='gpt-test', temperature=None)
    app.agent = None
    app.update_model_panel()
    assert fake_log.cleared is True
    # Only one write should have occurred with class name and model name
    assert any('LLM:' in m for m in fake_log.messages)
    assert any('gpt-test' in m for m in fake_log.messages)
    # Reset log for next subcase
    fake_log = FakeRichLog()
    app.query_one = lambda selector, cls=None: fake_log
    # Case 2: llm without model_name but with model attribute
    app.llm = FakeLLM(model=None, model_name=None, temperature=None)
    # set attribute model explicitly to test the elif branch
    app.llm.model = 'gpt-legacy'
    app.agent = None
    app.update_model_panel()
    assert fake_log.cleared is True
    assert any('gpt-legacy' in m for m in fake_log.messages)


def test_llm_with_agent_history_and_running_true_writes_durations_and_thinking():
    app, fake_log = setup_app_with_log()
    # Prepare LLM with temperature
    app.llm = FakeLLM(model_name='TestModel', temperature=0.5)
    # Prepare agent with settings.use_vision True
    agent = FakeAgent()
    agent.settings = FakeSettings(use_vision=True)
    # Prepare history: one step with metadata containing duration_seconds
    step_meta = SimpleMetadata(duration_seconds=1.25)
    step = HistoryStep(metadata=step_meta)
    agent.history = FakeHistory([step], total_duration=3.5)
    # Provide agent.state attribute so hasattr checks pass
    agent.state = types.SimpleNamespace(history=agent.history, paused=False)
    agent.running = True  # should trigger "LLM is thinking"
    app.agent = agent
    # Run
    app.update_model_panel()
    # Assertions: clear was called
    assert fake_log.cleared is True
    joined = " ".join(fake_log.messages)
    # Should include model name and temperature and vision indicator
    assert 'TestModel' in joined
    assert '0.5' in joined or '0.5ºC' in joined
    assert '+ vision' in joined
    # Should include total and last step durations
    assert 'Total Duration' in joined
    assert 'Last Step Duration' in joined
    # Should include thinking message
    assert 'LLM is thinking' in joined


def test_llm_with_agent_paused_and_no_total_duration_shows_paused_not_thinking():
    app, fake_log = setup_app_with_log()
    app.llm = FakeLLM(model_name='PausedModel', temperature=0)
    agent = FakeAgent()
    agent.settings = FakeSettings(use_vision=False)
    # History with a step that has no metadata (None) to trigger step_duration = 0 handling
    step = HistoryStep(metadata=None)
    agent.history = FakeHistory([step], total_duration=0.0)  # total_duration == 0 => no duration writes
    # Provide agent.state with paused True so paused branch triggers
    agent.state = types.SimpleNamespace(history=agent.history, paused=True)
    agent.running = False
    app.agent = agent
    # Run
    app.update_model_panel()
    assert fake_log.cleared is True
    joined = " ".join(fake_log.messages)
    # Should include model info line
    assert 'PausedModel' in joined
    # Should not include total/last duration since total_duration == 0
    assert 'Total Duration' not in joined
    assert 'Last Step Duration' not in joined
    # Should include paused message and not the thinking message
    assert 'LLM paused' in joined
    assert 'LLM is thinking' not in joined
