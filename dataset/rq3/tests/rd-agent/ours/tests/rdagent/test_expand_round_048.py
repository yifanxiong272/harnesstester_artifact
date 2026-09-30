import random
import types
import pytest

from rdagent.scenarios.data_science.proposal.exp_gen.select.expand import BackJumpCKPSelector


class _FB:
    def __init__(self, decision: bool):
        self.decision = decision


class FakeTrace:
    def __init__(self, hist, retrieve_list, all_exp_list, sota_list, sub_trace_count, NEW_ROOT=(999,)):
        self.hist = hist
        self._retrieve_list = retrieve_list
        self._all_exp_list = all_exp_list
        self._sota_list = sota_list
        self.sub_trace_count = sub_trace_count
        self.NEW_ROOT = NEW_ROOT

    def retrieve_search_list(self, search_type="ancestors"):
        return self._retrieve_list

    def experiment_and_feedback_list_after_init(self, return_type="all", search_type="ancestors"):
        # emulate the two-call behaviour in the source: one call for return_type="all" and
        # another call for return_type="sota". Return the prepared lists accordingly.
        if return_type == "all":
            return self._all_exp_list
        if return_type == "sota":
            return self._sota_list
        return []


def _make_selector(window=2, threshold=1, max_trace_num=2):
    sel = BackJumpCKPSelector()
    # Override constants to deterministic values for testing
    sel.SOTA_COUNT_WINDOW = window
    sel.SOTA_COUNT_THRESHOLD = threshold
    sel.MAX_TRACE_NUM = max_trace_num
    return sel


def test_not_enough_history_round_048():
    """When trace.hist is empty we must take the else branch and return (-1,)"""
    sel = _make_selector(window=2, threshold=1, max_trace_num=2)
    # hist empty triggers the final else block regardless of current_trace length
    trace = FakeTrace(hist=[], retrieve_list=[1, 2, 3, 4], all_exp_list=[], sota_list=[], sub_trace_count=0)

    result = sel.get_selection(trace)
    assert result == (-1,)


def test_sota_count_below_threshold_max_trace_reached_round_048():
    """If sota_count < threshold but we've reached MAX_TRACE_NUM, return (-1,)"""
    sel = _make_selector(window=2, threshold=10, max_trace_num=1)  # high threshold to ensure sota_count < threshold

    # Make current_trace longer than window so main if-entry is taken
    # all_exp_list contains two entries; fb.decision False to keep sota_count=0
    all_exp_list = [("e1", _FB(False)), ("e2", _FB(False)), ("e3", _FB(False))]
    trace_hist = ["h1"]  # non-empty hist
    trace = FakeTrace(hist=trace_hist, retrieve_list=[0, 1, 2, 3, 4], all_exp_list=all_exp_list, sota_list=[], sub_trace_count=1)

    result = sel.get_selection(trace)
    assert result == (-1,)


def test_random_less_than_half_returns_new_root_round_048(monkeypatch):
    """When sota_count < threshold and random.random() < 0.5 should return NEW_ROOT"""
    sel = _make_selector(window=2, threshold=10, max_trace_num=5)

    # Provide a window with no SOTA decisions
    all_exp_list = [("a", _FB(False)), ("b", _FB(False)), ("c", _FB(False))]
    trace = FakeTrace(hist=["x"], retrieve_list=[0, 1, 2, 3], all_exp_list=all_exp_list, sota_list=[], sub_trace_count=0, NEW_ROOT=(42,))

    # Force deterministic random choice < 0.5
    monkeypatch.setattr(random, "random", lambda: 0.3)

    result = sel.get_selection(trace)
    assert result == (42,)


def test_random_ge_half_sota_more_than_one_returns_index_round_048(monkeypatch):
    """When random >= 0.5 and there are >1 sota items, return index of last-second sota present in hist"""
    sel = _make_selector(window=2, threshold=10, max_trace_num=5)

    # all_exp_list used to form exp_list_in_window and compute fb.decision -> keep sota_count small
    all_exp_list = [("aa", _FB(False)), ("bb", _FB(False)), ("cc", _FB(False))]
    # hist contains these identifiers; sota_list items must match an item in hist for index()
    hist = ["X", "Y", "Z", "B_SOTA", "C_SOTA"]
    # Construct a sota list where last_two are "B_SOTA", "C_SOTA" so -2 refers to "B_SOTA"
    sota_list = ["onlyone", "B_SOTA", "C_SOTA"]
    trace = FakeTrace(hist=hist, retrieve_list=[1, 2, 3, 4, 5], all_exp_list=all_exp_list, sota_list=sota_list, sub_trace_count=0, NEW_ROOT=(7,))

    # Force deterministic random choice >= 0.5
    monkeypatch.setattr(random, "random", lambda: 0.6)

    result = sel.get_selection(trace)
    # last_second_sota_idx should be index of "B_SOTA" in hist
    assert result == (hist.index("B_SOTA"),)


def test_random_ge_half_sota_one_and_max_trace_reached_returns_minus1_round_048(monkeypatch):
    """When random >= 0.5 and only one sota exists but sub_trace_count >= MAX_TRACE_NUM, returns (-1,)"""
    sel = _make_selector(window=2, threshold=10, max_trace_num=1)

    all_exp_list = [("p", _FB(False)), ("q", _FB(False))]
    hist = ["only_sota_in_hist"]
    # sota_list with only one element
    sota_list = ["only_sota_in_hist"]
    trace = FakeTrace(hist=hist, retrieve_list=[0, 1, 2, 3], all_exp_list=all_exp_list, sota_list=sota_list, sub_trace_count=1, NEW_ROOT=(123,))

    monkeypatch.setattr(random, "random", lambda: 0.9)

    result = sel.get_selection(trace)
    assert result == (-1,)


def test_sota_count_above_threshold_continues_round_048():
    """When sota_count >= threshold the selector should continue current latest trial and return (-1,)"""
    sel = _make_selector(window=2, threshold=1, max_trace_num=5)

    # Build exp_list_in_window with at least one fb.decision True
    all_exp_list = [("t1", _FB(False)), ("t2", _FB(True)), ("t3", _FB(False))]
    trace = FakeTrace(hist=["h"], retrieve_list=[0, 1, 2], all_exp_list=all_exp_list, sota_list=[], sub_trace_count=0)

    result = sel.get_selection(trace)
    assert result == (-1,)
