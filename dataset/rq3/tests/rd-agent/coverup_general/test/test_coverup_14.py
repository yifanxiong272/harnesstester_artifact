# file: rdagent/log/ui/ds_user_interact.py:21-128
# asked: {"lines": [21, 23, 24, 25, 26, 27, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 41, 42, 43, 44, 45, 46, 49, 50, 51, 52, 54, 56, 57, 58, 59, 60, 61, 63, 64, 65, 66, 68, 69, 70, 71, 72, 74, 75, 76, 78, 79, 80, 82, 83, 84, 85, 88, 89, 90, 92, 93, 94, 95, 96, 97, 99, 100, 101, 102, 103, 105, 106, 107, 108, 111, 112, 114, 115, 116, 118, 119, 120, 122, 123, 124, 125, 128], "branches": [[23, 24], [23, 128], [25, 0], [25, 26], [34, 35], [34, 41], [49, 50], [49, 52], [70, 71], [70, 78], [74, 75], [74, 78], [82, 83], [82, 118], [83, 84], [83, 88], [118, 0], [118, 119]]}
# gained: {"lines": [21, 23, 24, 25, 26, 27, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 41, 42, 43, 44, 45, 46, 49, 50, 51, 52, 54, 56, 57, 58, 59, 60, 61, 63, 64, 65, 66, 68, 69, 70, 71, 72, 74, 75, 76, 78, 79, 80, 82, 83, 84, 85, 105, 106, 107, 108, 111, 112, 114, 115, 116, 118, 119, 120, 122, 123, 124, 125, 128], "branches": [[23, 24], [23, 128], [25, 26], [34, 35], [34, 41], [49, 50], [49, 52], [70, 71], [70, 78], [74, 75], [74, 78], [82, 83], [82, 118], [83, 84], [118, 0], [118, 119]]}

import json
import pickle
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import rdagent.log.ui.ds_user_interact as ds_ui


class _CtxManager:
    def __init__(self, name=None):
        self.name = name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeSt:
    def __init__(self):
        self.titles = []
        self.subheaders = []
        self.codes = []
        self.texts = []
        self.captions = []
        self.success_messages = []
        self.warnings = []
        self._form_submit_responses = []
        self._button_response = False
        # text_area will by default return the provided value argument
        # unless an override mapping is provided
        self._text_area_override = {}

    def title(self, *args, **kwargs):
        self.titles.append((args, kwargs))

    def subheader(self, *args, **kwargs):
        self.subheaders.append((args, kwargs))

    def code(self, *args, **kwargs):
        # store args and kwargs for assertions
        self.codes.append((args, kwargs))
        return "CODE"

    def text(self, *args, **kwargs):
        self.texts.append((args, kwargs))

    def caption(self, *args, **kwargs):
        self.captions.append((args, kwargs))

    def text_area(self, *args, **kwargs):
        label = args[0] if args else kwargs.get("label", "")
        if label in self._text_area_override:
            return self._text_area_override[label]
        # default behavior: return the `value` kwarg if present
        return kwargs.get("value", "")

    def form_submit_button(self, *args, **kwargs):
        if not self._form_submit_responses:
            return False
        return self._form_submit_responses.pop(0)

    def form(self, *args, **kwargs):
        return _CtxManager("form")

    def tabs(self, labels):
        # return context managers for each tab
        return [_CtxManager(l) for l in labels]

    def form_submit_sequence(self, seq):
        # provide a sequence of booleans to be returned on successive calls
        self._form_submit_responses = list(seq)

    def button(self, *args, **kwargs):
        return self._button_response

    def set_button_response(self, val):
        self._button_response = val

    def success(self, *args, **kwargs):
        self.success_messages.append((args, kwargs))

    def warning(self, *args, **kwargs):
        self.warnings.append((args, kwargs))


@pytest.fixture(autouse=True)
def isolate_module(monkeypatch, tmp_path):
    """
    Ensure each test gets a clean fake st and state and a temporary folder for DS_RD_SETTING.
    Also stub out time.sleep to avoid delays.
    """
    fake_st = FakeSt()
    monkeypatch.setattr(ds_ui, "st", fake_st)
    # create a simple session_state-like object
    fake_state = SimpleNamespace(selected_session_name=None, sessions={})
    monkeypatch.setattr(ds_ui, "state", fake_state)
    # patch DS_RD_SETTING.user_interaction_mid_folder to tmp_path
    if not hasattr(ds_ui, "DS_RD_SETTING") or not hasattr(ds_ui.DS_RD_SETTING, "user_interaction_mid_folder"):
        # create a simple holder
        class _S:
            pass
        ds_ui.DS_RD_SETTING = _S()
    ds_ui.DS_RD_SETTING.user_interaction_mid_folder = tmp_path
    # patch time.sleep to no-op
    monkeypatch.setattr(ds_ui, "time", SimpleNamespace(sleep=lambda s: None))
    yield


def test_render_main_content_no_selection(monkeypatch):
    # When no session selected, should call st.warning
    ds_ui.state.selected_session_name = None
    # ensure sessions empty
    ds_ui.state.sessions = {}
    ds_ui.render_main_content()
    # The fake st.warning should have been called once with the expected message
    assert ds_ui.st.warnings, "st.warning was not called"
    found = any("Please select a session from the sidebar." in args[0] for args, _ in ds_ui.st.warnings)
    assert found, "Warning message not as expected"


def test_render_main_content_with_approve_and_current_code(tmp_path, monkeypatch):
    """
    Test the branch where a session is selected, current_code non-empty,
    and the user clicks 'Approve without changes'. Should write a _RET.json
    file with {"action":"confirm"} and set selected_session_name to None.
    """
    # Prepare session data
    sess_name = "sess_approve"
    # target_hypothesis and task objects
    class H:
        def __init__(self, hypothesis):
            self.hypothesis = hypothesis

    class T:
        def __init__(self, description):
            self.description = description

    selected_session_data = {
        "competition": "compX",
        "scenario_description": "scenario: test",
        "ds_trace_desc": "trace: none",
        "current_code": "print('hello')",
        "hypothesis_candidates": ["h1", {"h": 2}],
        "target_hypothesis_index": 1,
        "target_hypothesis": H("orig_hyp"),
        "task": T("orig_task"),
        "user_instruction": None,
        # include some former instructions to exercise that loop
        "former_user_instructions": ["former1"],
    }
    # place in state
    ds_ui.state.selected_session_name = sess_name
    ds_ui.state.sessions = {sess_name: selected_session_data}

    # Configure fake st behavior:
    # text_area should by default return the provided value (original hypothesis and task)
    # The form_submit_button should return [False, True] meaning approve True on second call
    ds_ui.st.form_submit_sequence([False, True])
    # also set override for Former user instruction and Add new user instruction if needed
    ds_ui.st._text_area_override["Former user instruction"] = "former1"
    ds_ui.st._text_area_override["Add new user instruction"] = ""

    # Ensure no pkl exists (unlink will be called with missing_ok=True)
    pkl_path = ds_ui.DS_RD_SETTING.user_interaction_mid_folder / f"{sess_name}.pkl"
    if pkl_path.exists():
        pkl_path.unlink()

    # Run
    ds_ui.render_main_content()

    # After approve, a file named sess_approve_RET.json should exist with {"action":"confirm"}
    ret_json = ds_ui.DS_RD_SETTING.user_interaction_mid_folder / f"{sess_name}_RET.json"
    assert ret_json.exists(), "RET.json file not created"
    with open(ret_json, "r") as fh:
        data = json.load(fh)
    assert data == {"action": "confirm"}

    # selected_session_name should have been reset to None
    assert ds_ui.state.selected_session_name is None

    # clean up created json
    ret_json.unlink()


def test_render_main_content_extend_expiration(tmp_path, monkeypatch):
    """
    Test the Extend expiration by 60s branch. Ensure the pkl file is loaded,
    its 'expired_datetime' incremented by 60 seconds, and re-dumped.
    """
    sess_name = "sess_extend"
    # create session data minimal
    selected_session_data = {
        "competition": "compY",
        "scenario_description": "",
        "ds_trace_desc": "",
        "current_code": "",
        "hypothesis_candidates": [],
        "target_hypothesis_index": -1,
        "target_hypothesis": SimpleNamespace(hypothesis="h"),
        "task": SimpleNamespace(description="t"),
        "user_instruction": None,
        "former_user_instructions": None,
    }
    ds_ui.state.selected_session_name = sess_name
    ds_ui.state.sessions = {sess_name: selected_session_data}

    # Configure form buttons to be False so submission branch not taken
    ds_ui.st.form_submit_sequence([False, False])
    # Configure st.button (the Extend expiration) to return True
    ds_ui.st.set_button_response(True)

    # Create a pkl file with an expired_datetime
    pkl_path = ds_ui.DS_RD_SETTING.user_interaction_mid_folder / f"{sess_name}.pkl"
    orig_dt = datetime.now()
    session_data = {"expired_datetime": orig_dt}
    with open(pkl_path, "wb") as fh:
        pickle.dump(session_data, fh)

    # Run
    ds_ui.render_main_content()

    # Reload pkl and verify expired_datetime increased by 60 seconds
    with open(pkl_path, "rb") as fh:
        new_session_data = pickle.load(fh)
    assert "expired_datetime" in new_session_data
    assert new_session_data["expired_datetime"] == orig_dt + timedelta(seconds=60)
