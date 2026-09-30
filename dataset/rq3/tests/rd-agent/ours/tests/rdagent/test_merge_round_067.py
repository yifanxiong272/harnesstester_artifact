import pytest
from datetime import timedelta

import rdagent.scenarios.data_science.proposal.exp_gen.merge as merge_mod


class _FakeTimer:
    def __init__(self, td: timedelta):
        self._td = td

    def remain_time(self):
        return self._td


class _FakeTrace:
    NEW_ROOT = ("NEW_ROOT",)

    def __init__(self, hist=None, current_selection=(1,), sub_trace_count=0, leaves=None):
        self.hist = [] if hist is None else hist
        self._current_selection = tuple(current_selection)
        self.sub_trace_count = sub_trace_count
        self._leaves = [] if leaves is None else list(leaves)

        # record of last set_current_selection call for assertions
        self.last_set = None

    def get_current_selection(self):
        return tuple(self._current_selection)

    def get_leaves(self):
        return list(self._leaves)

    def set_current_selection(self, selection=None):
        # mimic signature used in the code: sometimes called with trace.NEW_ROOT (no kw) or with selection=...
        if selection is None:
            # if call used positional arg
            self.last_set = None
        else:
            self.last_set = selection
            self._current_selection = tuple(selection)


class _FakeExpGen:
    def __init__(self, result):
        self._result = result
        self.called_with = None

    def gen(self, trace):
        # record trace identity for assertion
        self.called_with = trace
        return self._result


class _FakeMergeExpGen(_FakeExpGen):
    pass


def _make_instance_without_init():
    # create object without running __init__ to avoid dependencies
    cls = merge_mod.ExpGen2TraceAndMergeV2
    inst = cls.__new__(cls)
    # set attributes that gen() expects
    inst.flag_start_merge = False
    inst.exp_gen = _FakeExpGen(result=("exp_gen_result",))
    inst.merge_exp_gen = _FakeMergeExpGen(result=("merge_exp_gen_result",))
    return inst


def test_high_time_no_multi_round_067(monkeypatch):
    """
    Timer has plenty of time and multi-version is disabled: should call exp_gen.gen and return its value.
    Covers lines: 373-376, 392
    """
    inst = _make_instance_without_init()

    # patch timer to a large remaining time
    monkeypatch.setattr(merge_mod.RD_Agent_TIMER_wrapper, "timer", _FakeTimer(timedelta(hours=10)))

    # ensure multi-version path disabled so no version parsing or resets are attempted
    monkeypatch.setattr(merge_mod, "DS_RD_SETTING", merge_mod.DS_RD_SETTING)
    merge_mod.DS_RD_SETTING.enable_multi_version_exp_gen = False
    merge_mod.DS_RD_SETTING.merge_hours = 1

    trace = _FakeTrace(hist=[1], current_selection=(1,), sub_trace_count=0)

    out = inst.gen(trace)
    assert out == ("exp_gen_result",)
    assert inst.exp_gen.called_with is trace


def test_high_time_multi_invalid_version_raises_assertion_round_067(monkeypatch):
    """
    When multi-version is enabled and the configured versions string contains an invalid token,
    the code should assert. This exercises the for-version assertion branch.
    Covers lines: 376-381
    """
    inst = _make_instance_without_init()

    # timer indicates plenty of time
    monkeypatch.setattr(merge_mod.RD_Agent_TIMER_wrapper, "timer", _FakeTimer(timedelta(hours=5)))

    # enable multi-version and inject an invalid version token
    monkeypatch.setattr(merge_mod, "DS_RD_SETTING", merge_mod.DS_RD_SETTING)
    merge_mod.DS_RD_SETTING.enable_multi_version_exp_gen = True
    merge_mod.DS_RD_SETTING.exp_gen_version_list = "v2,INVALID"
    merge_mod.DS_RD_SETTING.merge_hours = 1

    trace = _FakeTrace(hist=[1], current_selection=(1,), sub_trace_count=0)

    with pytest.raises(AssertionError):
        inst.gen(trace)


def test_low_time_less_than_two_leaves_returns_expgen_round_067(monkeypatch):
    """
    When merging stage (low remaining time) and fewer than two leaves, should set selection to (-1,) and call exp_gen.gen.
    Covers lines: 394-402
    """
    inst = _make_instance_without_init()

    # timer is low
    monkeypatch.setattr(merge_mod.RD_Agent_TIMER_wrapper, "timer", _FakeTimer(timedelta(minutes=0)))
    monkeypatch.setattr(merge_mod, "DS_RD_SETTING", merge_mod.DS_RD_SETTING)
    merge_mod.DS_RD_SETTING.merge_hours = 10  # ensure remain_time < merge_hours

    # leaves fewer than 2
    trace = _FakeTrace(hist=[1], current_selection=(1,), sub_trace_count=0, leaves=[42])

    out = inst.gen(trace)
    # verify branch behavior: selection set to (-1,) and exp_gen called
    assert trace.last_set == (-1,)
    assert out == ("exp_gen_result",)
    assert inst.exp_gen.called_with is trace


def test_low_time_start_merge_then_after_merge_round_067(monkeypatch):
    """
    Two-step scenario:
    - First call: merging stage, leaves >= 2, flag_start_merge False -> should set flag True, set NEW_ROOT and call merge_exp_gen.gen
    - Second call: merging stage again, flag_start_merge True -> should set selection (-1,) and call exp_gen.gen
    Covers lines: 399-411 (branches for flag_start_merge True/False)
    """
    inst = _make_instance_without_init()

    monkeypatch.setattr(merge_mod.RD_Agent_TIMER_wrapper, "timer", _FakeTimer(timedelta(minutes=0)))
    monkeypatch.setattr(merge_mod, "DS_RD_SETTING", merge_mod.DS_RD_SETTING)
    merge_mod.DS_RD_SETTING.merge_hours = 10

    # make a trace with at least 2 leaves
    trace = _FakeTrace(hist=[1], current_selection=(), sub_trace_count=1, leaves=[1, 2])

    # First call: should trigger merge_exp_gen.gen and set_current_selection(trace.NEW_ROOT)
    out1 = inst.gen(trace)
    assert inst.flag_start_merge is True
    assert trace.last_set == trace.NEW_ROOT
    assert out1 == ("merge_exp_gen_result",)

    # Prepare for second call: now flag_start_merge True
    # Also update trace state to simulate continuation (leaves still >=2)
    trace.last_set = None
    out2 = inst.gen(trace)
    assert trace.last_set == (-1,)
    assert out2 == ("exp_gen_result",)
