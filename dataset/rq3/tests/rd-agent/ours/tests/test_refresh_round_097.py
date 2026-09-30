import sys
# Ensure argparse.parse_args() in the module import sees a benign argv and does not call sys.exit
sys.argv = [sys.argv[0]]

from pathlib import Path
import types
import pytest

import rdagent.log.ui.app as app

class StubState:
    def __init__(self):
        self.log_path = Path("logs.txt")
        self.fs = None
        self.msgs = {"preexisting": True}
        self.lround = 999
        self.erounds = {"x": 5}
        self.e_decisions = {"a": (1,)}
        self.hypotheses = {"h": None}
        self.h_decisions = {"h": True}
        self.metric_series = [1]
        self.all_metric_series = [2]
        self.last_msg = None
        self.current_tags = ["t"]
        self.alpha_baseline_metrics = {"m": 1}
        self.scenario = "old"

class DummyFileStorage:
    def __init__(self, path):
        self.path = path
    def iter_msg(self):
        return iter([types.SimpleNamespace(content="a")])

class SimpleST:
    def __init__(self):
        self.toast_calls = []
        self.write_calls = []
    def toast(self, msg, icon=None):
        self.toast_calls.append((msg, icon))
    def write(self, *args, **kwargs):
        self.write_calls.append((args, kwargs))

def test_refresh_early_return_round_097(monkeypatch):
    """When state.log_path is None, refresh should return early and call st.toast with the expected message."""
    s = StubState()
    s.log_path = None
    st = SimpleST()
    monkeypatch.setattr(app, "state", s)
    monkeypatch.setattr(app, "st", st)

    result = app.refresh()

    assert result is None
    assert len(st.toast_calls) == 1
    msg, icon = st.toast_calls[0]
    assert ":red[**Please Set Log Path!**]" in msg
    assert icon is not None

def test_refresh_with_main_log_path_and_same_trace_round_097(monkeypatch, tmp_path):
    """When main_log_path is truthy and same_trace=True, FileStorage should be constructed with main_log_path / state.log_path and state should be reinitialized."""
    s = StubState()
    s.log_path = Path("subdir/logfile.log")
    st = SimpleST()
    main_base = tmp_path / "base"
    monkeypatch.setattr(app, "main_log_path", main_base)
    monkeypatch.setattr(app, "state", s)
    monkeypatch.setattr(app, "st", st)

    created = {}
    class RecordingFS(DummyFileStorage):
        def __init__(self, path):
            super().__init__(path)
            created['path'] = path
    monkeypatch.setattr(app, "FileStorage", RecordingFS)

    app.refresh(same_trace=True)

    assert 'path' in created
    assert created['path'] == main_base / s.log_path

    # state.fs should be an iterator
    assert hasattr(app.state, 'fs') and hasattr(app.state.fs, '__iter__')

    # verify resets to expected shapes
    assert app.state.lround == 0
    assert app.state.erounds.get('new', 0) == 0
    # e_decisions is a defaultdict(lambda: defaultdict(tuple)) -> nested access yields tuple
    nested = app.state.e_decisions['x']
    assert isinstance(nested, dict) or hasattr(nested, '__getitem__')
    # hypotheses was reinitialized as defaultdict(None) in source; check the default_factory rather than accessing missing key
    assert getattr(app.state.hypotheses, 'default_factory', None) is None
    # h_decisions default False
    assert app.state.h_decisions.get('flag', False) is False
    assert app.state.metric_series == []
    assert app.state.all_metric_series == []
    assert app.state.last_msg is None
    assert app.state.current_tags == []
    assert app.state.alpha_baseline_metrics is None

def test_refresh_scenario_detection_branches_round_097(monkeypatch):
    """Test both no-scenario-detected and scenario-detected branches when same_trace=False. Also exercise main_log_path falsy branch."""
    s = StubState()
    s.log_path = Path("logs_for_detection.log")
    st = SimpleST()
    monkeypatch.setattr(app, "state", s)
    monkeypatch.setattr(app, "st", st)
    monkeypatch.setattr(app, "main_log_path", None)
    monkeypatch.setattr(app, "FileStorage", DummyFileStorage)

    # Case A: no scenario detected
    def fake_get_msgs_until_none(pred):
        app.state.last_msg = None
    monkeypatch.setattr(app, "get_msgs_until", fake_get_msgs_until_none)

    pre_msgs = dict(app.state.msgs)
    app.refresh(same_trace=False)

    # st.write should have been called with the preexisting msgs
    assert any(pre_msgs == call_args[0][0] for call_args in st.write_calls)
    assert app.state.scenario is None

    # Case B: scenario detected
    class FakeScenario:
        pass
    last_msg_obj = types.SimpleNamespace(content=FakeScenario())
    def fake_get_msgs_until_found(pred):
        app.state.last_msg = last_msg_obj
    monkeypatch.setattr(app, "get_msgs_until", fake_get_msgs_until_found)
    monkeypatch.setattr(app, "Scenario", FakeScenario)

    st.toast_calls.clear()
    st.write_calls.clear()

    app.refresh(same_trace=False)

    assert isinstance(app.state.scenario, FakeScenario)
    assert any("Scenario Info detected" in msg for msg, _ in st.toast_calls)
