# file: rdagent/scenarios/data_science/proposal/exp_gen/select/expand.py:175-241
# asked: {"lines": [176, 178, 180, 182, 185, 186, 187, 188, 190, 192, 193, 194, 196, 197, 199, 200, 201, 202, 204, 206, 207, 209, 210, 211, 212, 213, 215, 216, 219, 220, 221, 223, 224, 226, 227, 229, 230, 233, 234, 236, 237, 239, 240, 241], "branches": [[178, 180], [178, 239], [186, 187], [186, 190], [187, 186], [187, 188], [190, 192], [190, 233], [192, 193], [192, 199], [200, 201], [200, 206], [210, 211], [210, 219], [219, 220], [219, 226]]}
# gained: {"lines": [176, 178, 180, 182, 185, 186, 187, 188, 190, 192, 193, 194, 196, 197, 199, 200, 201, 202, 204, 206, 207, 209, 210, 211, 212, 213, 215, 216, 219, 220, 221, 223, 224, 233, 234, 236, 237, 239, 240, 241], "branches": [[178, 180], [178, 239], [186, 187], [186, 190], [187, 186], [187, 188], [190, 192], [190, 233], [192, 193], [192, 199], [200, 201], [200, 206], [210, 211], [210, 219], [219, 220]]}

import types
import random
import pytest

from rdagent.scenarios.data_science.proposal.exp_gen.select.expand import BackJumpCKPSelector


class FakeFB:
    def __init__(self, decision: bool):
        self.decision = decision


class FakeTrace:
    NEW_ROOT = ()

    def __init__(self, hist, all_list, sota_list, current_search_list, initial_sub_trace_count=0,
                 dynamic_sub_trace_counts=None):
        """
        hist: list of nodes (exp, fb)
        all_list: list returned for experiment_and_feedback_list_after_init(return_type='all', ...)
        sota_list: list returned for experiment_and_feedback_list_after_init(return_type='sota', ...)
        current_search_list: list returned for retrieve_search_list(...)
        initial_sub_trace_count: integer used if dynamic_sub_trace_counts is None
        dynamic_sub_trace_counts: optional iterable of values to return on successive accesses of sub_trace_count
        """
        self.hist = list(hist)
        self._all_list = list(all_list)
        self._sota_list = list(sota_list)
        self._current_search_list = list(current_search_list)
        self._sub_trace_count_value = initial_sub_trace_count
        self._dynamic_counts = None
        if dynamic_sub_trace_counts is not None:
            self._dynamic_counts = iter(dynamic_sub_trace_counts)
            # consume first value as current to mimic first-access behavior
        self._sub_trace_accesses = 0

    def retrieve_search_list(self, search_type="ancestors"):
        return list(self._current_search_list)

    def experiment_and_feedback_list_after_init(self, return_type="all", search_type="ancestors"):
        if return_type == "all":
            return list(self._all_list)
        elif return_type == "sota":
            return list(self._sota_list)
        else:
            return []

    @property
    def sub_trace_count(self):
        # If dynamic counts provided, return next value each access.
        if self._dynamic_counts is not None:
            try:
                val = next(self._dynamic_counts)
                return val
            except StopIteration:
                # If exhausted, return last known or provided static
                return self._sub_trace_count_value
        return self._sub_trace_count_value


def make_node(name, decision):
    return (name, FakeFB(decision))


def test_not_enough_history_returns_continue():
    selector = BackJumpCKPSelector()
    # Make window > current_search_list length to trigger "Not enough history"
    selector.SOTA_COUNT_WINDOW = 3

    # hist non-empty but current_search_list length <= SOTA_COUNT_WINDOW
    hist = [make_node("e1", False)]
    current_search = [hist[0]]  # length 1 <= 3
    all_list = [hist[0]]
    sota_list = [hist[0]]

    t = FakeTrace(hist=hist, all_list=all_list, sota_list=sota_list, current_search_list=current_search,
                  initial_sub_trace_count=0)
    res = selector.get_selection(t)
    assert res == (-1,)  # continue current latest trial


def test_sota_count_above_threshold_continues_current_trial():
    selector = BackJumpCKPSelector()
    selector.SOTA_COUNT_WINDOW = 1
    selector.SOTA_COUNT_THRESHOLD = 1

    # create current_search_list longer than window
    node = make_node("e1", True)  # decision True yields sota_count = 1
    hist = [node]
    current_search = [node, node]  # length 2 > window
    all_list = [node, node, node]  # last window slice will include at least one with decision True
    sota_list = [node]

    t = FakeTrace(hist=hist, all_list=all_list, sota_list=sota_list, current_search_list=current_search,
                  initial_sub_trace_count=0)
    res = selector.get_selection(t)
    assert res == (-1,)  # sota_count >= threshold -> continue current trial


def test_sota_count_below_threshold_max_trace_reached_returns_minus_one():
    selector = BackJumpCKPSelector()
    selector.SOTA_COUNT_WINDOW = 1
    selector.SOTA_COUNT_THRESHOLD = 1
    # set MAX_TRACE_NUM small to test reaching it
    selector.MAX_TRACE_NUM = 2

    # create current_search_list longer than window
    node = make_node("e1", False)  # decision False -> sota_count = 0
    hist = [node]
    current_search = [node, node]
    all_list = [node, node]
    sota_list = []

    # sub_trace_count >= MAX_TRACE_NUM triggers early return (-1,)
    t = FakeTrace(hist=hist, all_list=all_list, sota_list=sota_list, current_search_list=current_search,
                  initial_sub_trace_count=2)
    res = selector.get_selection(t)
    assert res == (-1,)


def test_sota_count_below_threshold_random_new_root(monkeypatch):
    selector = BackJumpCKPSelector()
    selector.SOTA_COUNT_WINDOW = 1
    selector.SOTA_COUNT_THRESHOLD = 1
    selector.MAX_TRACE_NUM = 10

    node = make_node("e1", False)
    hist = [node]
    current_search = [node, node]
    all_list = [node, node]
    sota_list = []

    t = FakeTrace(hist=hist, all_list=all_list, sota_list=sota_list, current_search_list=current_search,
                  initial_sub_trace_count=0)

    # Force random.random() < 0.5 to take NEW_ROOT branch
    monkeypatch.setattr(random, "random", lambda: 0.1)
    res = selector.get_selection(t)
    assert res == t.NEW_ROOT  # reboot a new sub-trace


def test_sota_count_below_threshold_random_jump_to_last_second_sota():
    selector = BackJumpCKPSelector()
    selector.SOTA_COUNT_WINDOW = 2
    selector.SOTA_COUNT_THRESHOLD = 2
    selector.MAX_TRACE_NUM = 10

    # Create hist with multiple nodes; we'll make sota_list contain the last two
    n1 = make_node("e1", False)
    n2 = make_node("e2", True)
    n3 = make_node("e3", True)
    hist = [n1, n2, n3]
    current_search = [n1, n2, n3, n1]  # length 4 > window=2
    # all_list ends with window elements (we'll make them non-SOTA decisions so sota_count < threshold)
    all_list = [n1, n1, n1, n1]
    # sota_list with >1 items: last second SOTA is n2
    sota_list = [n2, n3]

    t = FakeTrace(hist=hist, all_list=all_list, sota_list=sota_list, current_search_list=current_search,
                  initial_sub_trace_count=0)

    # Force random.random() >= 0.5 to take the jump-to-last-second-sota branch
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(random, "random", lambda: 0.9)
    try:
        res = selector.get_selection(t)
    finally:
        monkeypatch.undo()

    # last second SOTA is n2 which is at index 1 in hist
    assert res == (1,)


def test_dynamic_sub_trace_count_inner_max_trace_check(monkeypatch):
    selector = BackJumpCKPSelector()
    selector.SOTA_COUNT_WINDOW = 1
    selector.SOTA_COUNT_THRESHOLD = 1
    selector.MAX_TRACE_NUM = 3

    node = make_node("e1", False)
    hist = [node]
    current_search = [node, node]
    all_list = [node, node]
    # sota_list length <= 1 to force inner else branch
    sota_list = [node]

    # dynamic_sub_trace_counts will return 0 on first access (so outer check passes),
    # then return 3 on second access (so inner check triggers)
    t = FakeTrace(hist=hist, all_list=all_list, sota_list=sota_list, current_search_list=current_search,
                  dynamic_sub_trace_counts=[0, 3])

    # Force random.random() >= 0.5, so code goes into the branch with sota_list handling
    monkeypatch.setattr(random, "random", lambda: 0.9)
    res = selector.get_selection(t)
    assert res == (-1,)  # inner second check sees sub_trace_count >= MAX_TRACE_NUM and returns (-1,)
