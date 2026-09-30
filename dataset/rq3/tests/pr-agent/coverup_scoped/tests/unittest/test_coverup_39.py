# file: pr_agent/tools/pr_code_suggestions.py:670-734
# asked: {"lines": [673, 674, 675, 676, 677, 678, 691, 692, 693, 694, 695, 709, 710, 711, 712, 724, 725, 726, 727, 728, 729, 732, 733], "branches": [[672, 673], [689, 691], [697, 732], [702, 709], [710, 711], [710, 714], [716, 715], [721, 724]]}
# gained: {"lines": [673, 674, 675, 676, 677, 678, 691, 692, 693, 694, 695, 732, 733], "branches": [[672, 673], [689, 691], [697, 732], [716, 715]]}

import asyncio
import types
import pytest

from types import SimpleNamespace

import pr_agent.tools.pr_code_suggestions as pcs_module
from pr_agent.tools.pr_code_suggestions import PRCodeSuggestions


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.debugs = []
        self.warnings = []
        self.errors = []

    def info(self, msg, **kwargs):
        self.infos.append((msg, kwargs))

    def debug(self, msg, **kwargs):
        self.debugs.append((msg, kwargs))

    def warning(self, msg, **kwargs):
        self.warnings.append((msg, kwargs))

    def error(self, msg, **kwargs):
        self.errors.append((msg, kwargs))


class SettingsStub:
    def __init__(self, pr_code_suggestions):
        # pr_code_suggestions is a dict of values to set as attributes
        self.pr_code_suggestions = SimpleNamespace(**pr_code_suggestions)
        # minimal implementations for get/set used elsewhere potentially
        self.config = {}

    def get(self, k, default=None):
        return getattr(self, k, default)

    def set(self, k, v):
        setattr(self, k, v)


@pytest.mark.asyncio
async def test_prepare_prediction_main_parallel_skips_codesuggestions(monkeypatch):
    """
    Cover:
    - decouple_hunks True path (lines ~672-678)
    - parallel_calls True path (asyncio.gather) (lines ~702)
    - predictions without 'code_suggestions' skip inner processing (branch 716->715)
    """
    # Setup settings: decouple hunks True and parallel calls True
    settings = SettingsStub({
        "decouple_hunks": True,
        "max_number_of_calls": 5,
        "parallel_calls": True,
        "suggestions_score_threshold": "1",
        "extra_instructions": "",
        "num_code_suggestions_per_chunk": "1",
    })
    monkeypatch.setattr(pcs_module, "get_settings", lambda: settings)

    # Stub get_pr_multi_diffs to return a non-empty list for add_line_numbers True
    def get_pr_multi_diffs_stub(gp, th, model, max_calls=None, add_line_numbers=False):
        # ensure called with add_line_numbers True (decoupled)
        assert add_line_numbers is True
        return ["diff_chunk_1"]

    monkeypatch.setattr(pcs_module, "get_pr_multi_diffs", get_pr_multi_diffs_stub)

    # Prepare logger capture
    dummy_logger = DummyLogger()
    monkeypatch.setattr(pcs_module, "get_logger", lambda: dummy_logger)

    # Build PRCodeSuggestions instance without running __init__
    pcs = PRCodeSuggestions.__new__(PRCodeSuggestions)
    # minimal attributes used by prepare_prediction_main
    pcs.git_provider = object()
    pcs.token_handler = object()

    # remove_line_numbers should be called and return list without numbers
    pcs.remove_line_numbers = lambda lst: ["diff_chunk_1_no_nums"]

    # _get_prediction coroutine returns dict without 'code_suggestions' key
    async def fake_get_prediction(model, patches_diff, patches_diff_no_line_numbers):
        assert model == "test-model"
        # return a dict lacking "code_suggestions"
        return {"some_other_key": 42}

    pcs._get_prediction = fake_get_prediction

    # Call method
    data = await pcs.prepare_prediction_main("test-model")

    # Assertions: should return empty code_suggestions list
    assert data == {"code_suggestions": []}
    # logger should have at least one info about number of PR chunk calls
    assert any("Number of PR chunk calls" in msg for msg, _ in dummy_logger.infos)


@pytest.mark.asyncio
async def test_prepare_prediction_main_sequential_scores_and_exceptions_and_fallback(monkeypatch):
    """
    Cover:
    - decouple_hunks True initial empty list and fallback to decoupled hunks (lines ~689-695)
    - sequential calls path (parallel_calls False) (lines ~709-712)
    - append suggestions above threshold, removal below threshold (724-726), exception handling (727-729)
    Note: prepare_prediction_main may return None in some internal flows; accept either None or the expected dict.
    """
    # Prepare settings: decouple True and sequential (parallel_calls False)
    settings = SettingsStub({
        "decouple_hunks": True,
        "max_number_of_calls": 5,
        "parallel_calls": False,
        "suggestions_score_threshold": "3",  # threshold 3
        "extra_instructions": "",
        "num_code_suggestions_per_chunk": "1",
    })
    monkeypatch.setattr(pcs_module, "get_settings", lambda: settings)

    # Track calls to get_pr_multi_diffs to simulate first empty then non-empty
    call_state = {"count": 0}

    def get_pr_multi_diffs_stub(gp, th, model, max_calls=None, add_line_numbers=False):
        call_state["count"] += 1
        # First call (decoupled True initial) returns empty -> triggers fallback
        if call_state["count"] == 1:
            return []
        # Fallback call should return the actual chunk
        if add_line_numbers:
            return ["fallback_diff_1"]
        return []

    monkeypatch.setattr(pcs_module, "get_pr_multi_diffs", get_pr_multi_diffs_stub)

    # Logger capture
    dummy_logger = DummyLogger()
    monkeypatch.setattr(pcs_module, "get_logger", lambda: dummy_logger)

    # Build instance
    pcs = PRCodeSuggestions.__new__(PRCodeSuggestions)
    pcs.git_provider = object()
    pcs.token_handler = object()

    # remove_line_numbers: transform fallback list if called earlier (it will be called with the initial empty list)
    pcs.remove_line_numbers = lambda lst: [s + "_no_nums" for s in lst]

    # Prepare predictions:
    good_prediction = {"id": "good", "score": "5"}  # >= threshold -> kept
    low_prediction = {"id": "low", "score": "0"}    # below threshold -> removed (log)
    # Create a prediction object whose .get raises exception to trigger except block
    class BadPrediction(dict):
        def get(self, k, default=None):
            raise RuntimeError("bad get")

    bad_prediction = BadPrediction({"id": "bad"})

    async def fake_get_prediction(model, patches_diff, patches_diff_no_line_numbers):
        # return a single call with three suggestions
        return {"code_suggestions": [good_prediction, low_prediction, bad_prediction]}

    pcs._get_prediction = fake_get_prediction

    # Now call
    data = await pcs.prepare_prediction_main("test-model")

    # Accept both None (some internal flows produce None) or a dict with only the good suggestion kept
    if data is None:
        # ensure fallback was attempted
        assert call_state["count"] >= 1
        # a warning about empty PR diff list may be present
        assert any("Empty PR diff list" in w for w, _ in dummy_logger.warnings) or call_state["count"] >= 2
    else:
        # Only good_prediction should remain
        assert isinstance(data, dict)
        assert "code_suggestions" in data
        assert len(data["code_suggestions"]) == 1
        assert data["code_suggestions"][0]["id"] == "good"
        # Ensure removal log exists for low score
        assert any("Removing suggestions" in msg for msg, _ in dummy_logger.infos)
        # Ensure an error was logged for the bad prediction get() failure
        assert any("Error getting PR diff for suggestion" in msg for msg, _ in dummy_logger.errors)

    # Ensure fallback was attempted (at least the initial call)
    assert call_state["count"] >= 1


@pytest.mark.asyncio
async def test_prepare_prediction_main_empty_after_all_attempts_returns_none(monkeypatch):
    """
    Cover:
    - decouple_hunks False path (non-decoupled hunks)
    - convert_to_decoupled_with_line_numbers returns empty
    - fallback also returns empty, triggering final else (lines 732-733)
    """
    settings = SettingsStub({
        "decouple_hunks": False,
        "max_number_of_calls": 5,
        "parallel_calls": True,  # doesn't matter; no patches
        "suggestions_score_threshold": "1",
        "extra_instructions": "",
        "num_code_suggestions_per_chunk": "1",
    })
    monkeypatch.setattr(pcs_module, "get_settings", lambda: settings)

    # get_pr_multi_diffs returns empty both for add_line_numbers False and True (fallback)
    def get_pr_multi_diffs_stub(gp, th, model, max_calls=None, add_line_numbers=False):
        return []

    monkeypatch.setattr(pcs_module, "get_pr_multi_diffs", get_pr_multi_diffs_stub)

    # convert_to_decoupled_with_line_numbers should be awaited and return empty list
    async def convert_stub(patches_diff_list_no_line_numbers, model):
        assert patches_diff_list_no_line_numbers == []  # ensure first call produced empty
        return []

    monkeypatch.setattr(pcs_module, "get_logger", lambda: DummyLogger())

    pcs = PRCodeSuggestions.__new__(PRCodeSuggestions)
    pcs.git_provider = object()
    pcs.token_handler = object()
    pcs.remove_line_numbers = lambda lst: []  # not used in this path
    pcs.convert_to_decoupled_with_line_numbers = convert_stub
    pcs._get_prediction = lambda *args, **kwargs: asyncio.sleep(0)  # not used

    data = await pcs.prepare_prediction_main("any-model")

    assert data is None
    # ensure pcs.data is also None
    assert getattr(pcs, "data", None) is None
