# file: rdagent/scenarios/data_science/proposal/exp_gen/router/__init__.py:70-142
# asked: {"lines": [76, 77, 78, 80, 81, 83, 84, 85, 88, 90, 91, 92, 94, 95, 96, 97, 98, 99, 100, 102, 104, 105, 106, 107, 108, 111, 112, 113, 114, 115, 116, 118, 119, 120, 121, 124, 125, 126, 127, 128, 129, 130, 131, 133, 135, 136, 139, 140, 142], "branches": [[80, 81], [81, 83], [81, 142], [84, 85], [84, 90], [90, 91], [90, 94], [95, 96], [95, 100], [96, 97], [96, 100], [97, 96], [97, 98], [106, 111], [106, 113], [113, 118], [113, 124]]}
# gained: {"lines": [76, 77, 78, 80, 81, 83, 84, 85, 88, 90, 91, 92, 94, 95, 100, 102, 104, 105, 106, 107, 108, 111, 112, 113, 114, 115, 116, 118, 119, 120, 121, 124, 125, 126, 127, 128, 129, 130, 131, 133, 135, 136, 139, 140], "branches": [[80, 81], [81, 83], [84, 85], [84, 90], [90, 91], [90, 94], [95, 100], [106, 111], [106, 113], [113, 118], [113, 124]]}

import asyncio
from datetime import timedelta
import pytest

import rdagent.scenarios.data_science.proposal.exp_gen.router as router
from rdagent.scenarios.data_science.proposal.exp_gen.planner import DSExperimentPlan


class DummyTimer:
    def __init__(self, started: bool, remain_sec: float):
        self.started = started
        self._remain = timedelta(seconds=remain_sec)

    def remain_time(self):
        return self._remain


class DummyExp:
    def __init__(self, name="exp"):
        self.name = name
        self.local_selection = None
        self.plan = None
        self.set_local_selection_called = False

    def set_local_selection(self, sel):
        self.local_selection = sel
        self.set_local_selection_called = True


class DummyLoop:
    def __init__(self, loop_idx=0, unfinished=0):
        self.loop_idx = loop_idx
        self._unfinished = unfinished

    def get_unfinished_loop_cnt(self, idx):
        assert idx == self.loop_idx
        return self._unfinished


class DummyTrace:
    def __init__(self, leaves, sota_exp_to_submit=None, sota_exp_result=None):
        # leaves: list of ints
        self._leaves = list(leaves)
        self.sota_exp_to_submit = sota_exp_to_submit
        # value to return from sota_experiment(selection=...)
        self._sota_exp_result = sota_exp_result
        self.current_selection = None
        self.registered = []

    def get_leaves(self):
        return list(self._leaves)

    def set_current_selection(self, selection=None):
        # code sometimes calls with kw arg name selection, sometimes positional
        self.current_selection = selection

    def sota_experiment(self, selection=None):
        return self._sota_exp_result

    def is_parent(self, idx, leaf):
        # simple rule: parent if idx equals leaf - 1 (for testing)
        return idx == leaf - 1

    def exp2idx(self, exp):
        # make a simple mapping for sota_exp_to_submit -> int index if it's int
        return int(exp)

    def register_uncommitted_exp(self, exp, loop_idx):
        self.registered.append((exp, loop_idx))


class DummyScheduler:
    def __init__(self, *args, **kwargs):
        pass

    async def next(self, trace):
        # return a tuple for selection
        return (999,)


class DummyPlanner:
    def __init__(self, *args, **kwargs):
        pass

    def plan(self, trace):
        return DSExperimentPlan()


class DummyGen:
    def __init__(self, name, to_return=None):
        self.name = name
        self.to_return = to_return or DummyExp(name)

    def gen(self, trace, plan=None):
        return self.to_return


def test_async_gen_uses_draft_generator(monkeypatch):
    """
    Case A:
    - timer not started (so draft path possible)
    - trace.sota_experiment(selection) returns None
    - DS_RD_SETTING.enable_draft_before_first_sota True
    - ensure draft_exp_gen.gen used, selection set, and experiment registered
    """
    # Ensure import_class doesn't try to import unknown classes during __init__
    monkeypatch.setattr(router, "import_class", lambda path: DummyPlanner)

    # Timer: not started
    monkeypatch.setattr(router.RD_Agent_TIMER_wrapper, "timer", DummyTimer(started=False, remain_sec=3600 * 24))

    # RD agent settings: allow parallel -> patch method on class
    monkeypatch.setattr(type(router.RD_AGENT_SETTINGS), "get_max_parallel", lambda self: 10)

    # DS settings: enable draft_before_first_sota and disable planner
    monkeypatch.setattr(router.DS_RD_SETTING, "enable_draft_before_first_sota", True)
    monkeypatch.setattr(router.DS_RD_SETTING, "enable_planner", False)
    # ensure merge_hours set reasonable
    monkeypatch.setattr(router.DS_RD_SETTING, "merge_hours", 1)

    # Replace scheduler, gens on instance after creation
    gen = router.ParallelMultiTraceExpGen(scen=None)
    # override scheduler to deterministic one
    gen.trace_scheduler = DummyScheduler()
    # create a draft generator that returns specific DummyExp
    draft_exp = DummyExp(name="draft")
    gen.draft_exp_gen = DummyGen("draft", to_return=draft_exp)
    # also override other gens to avoid surprises
    default_exp = DummyExp(name="default")
    gen.exp_gen = DummyGen("default", to_return=default_exp)
    gen.merge_exp_gen = DummyGen("merge", to_return=DummyExp(name="merge"))

    # Logger no-op
    monkeypatch.setattr(router.logger, "info", lambda *a, **k: None)
    monkeypatch.setattr(router.logger, "log_object", lambda *a, **k: None)

    # Create trace and loop
    trace = DummyTrace(leaves=[1, 2, 3], sota_exp_to_submit=None, sota_exp_result=None)
    loop = DummyLoop(loop_idx=7, unfinished=0)

    # Call async_gen and assert draft path used
    exp = asyncio.run(gen.async_gen(trace, loop))
    assert exp is draft_exp
    assert exp.set_local_selection_called is True
    # ensure plan applied (DS_RD_SETTING.enable_planner False -> DSExperimentPlan used)
    assert isinstance(exp.plan, DSExperimentPlan)
    # ensure trace registered the experiment with correct loop index
    assert trace.registered and trace.registered[-1][0] is exp and trace.registered[-1][1] == loop.loop_idx


def test_async_gen_uses_merge_generator_and_updates_settings(monkeypatch):
    """
    Case B:
    - timer started and remain_time < merge_hours -> merge path
    - leaves length >= 2
    - ensure DS_RD_SETTING thresholds are set to 100000 and merge_exp_gen used
    """
    monkeypatch.setattr(router, "import_class", lambda path: DummyPlanner)

    # Timer started and small remaining time (below merge threshold)
    monkeypatch.setattr(router.RD_Agent_TIMER_wrapper, "timer", DummyTimer(started=True, remain_sec=1))

    # RD agent settings: allow parallel -> patch method on class
    monkeypatch.setattr(type(router.RD_AGENT_SETTINGS), "get_max_parallel", lambda self: 10)

    # DS settings: set merge_hours large so remain_time < merge_hours triggers
    monkeypatch.setattr(router.DS_RD_SETTING, "merge_hours", 24)
    monkeypatch.setattr(router.DS_RD_SETTING, "enable_planner", False)
    # keep draft_before_first_sota maybe True but merge condition takes precedence
    monkeypatch.setattr(router.DS_RD_SETTING, "enable_draft_before_first_sota", True)

    gen = router.ParallelMultiTraceExpGen(scen=None)
    gen.trace_scheduler = DummyScheduler()

    # create merge generator and track that it was used
    merge_exp = DummyExp(name="merge_used")
    gen.merge_exp_gen = DummyGen("merge", to_return=merge_exp)

    # other gens to safe defaults
    gen.draft_exp_gen = DummyGen("draft", to_return=DummyExp("draft"))
    gen.exp_gen = DummyGen("default", to_return=DummyExp("default"))

    # logger no-op
    monkeypatch.setattr(router.logger, "info", lambda *a, **k: None)
    monkeypatch.setattr(router.logger, "log_object", lambda *a, **k: None)

    # Ensure attributes exist and set initial values
    monkeypatch.setattr(router.DS_RD_SETTING, "coding_fail_reanalyze_threshold", 0)
    monkeypatch.setattr(router.DS_RD_SETTING, "consecutive_errors", 0)

    trace = DummyTrace(leaves=[10, 20], sota_exp_to_submit=None, sota_exp_result=None)
    loop = DummyLoop(loop_idx=3, unfinished=0)

    exp = asyncio.run(gen.async_gen(trace, loop))

    assert exp is merge_exp
    # After merge branch, DS_RD_SETTING thresholds set to 100000
    assert router.DS_RD_SETTING.coding_fail_reanalyze_threshold == 100000
    assert router.DS_RD_SETTING.consecutive_errors == 100000
    # ensure selection set and registration
    assert exp.set_local_selection_called
    assert trace.registered and trace.registered[-1][0] is exp and trace.registered[-1][1] == loop.loop_idx


def test_async_gen_small_leaves_uses_default_gen_and_selection_negative_one(monkeypatch):
    """
    - Timer started and remain_time < merge_hours (so inner else is executed)
    - but leaves length < 2 -> local_selection becomes (-1,)
    - Because len(leaves) < 2, merge isn't used; default exp_gen should be used
    """
    monkeypatch.setattr(router, "import_class", lambda path: DummyPlanner)

    # Timer started and small remaining time -> enter inner else where len(leaves) < 2
    monkeypatch.setattr(router.RD_Agent_TIMER_wrapper, "timer", DummyTimer(started=True, remain_sec=1))

    # RD agent settings: allow parallel -> patch method on class
    monkeypatch.setattr(type(router.RD_AGENT_SETTINGS), "get_max_parallel", lambda self: 10)

    monkeypatch.setattr(router.DS_RD_SETTING, "merge_hours", 24)
    monkeypatch.setattr(router.DS_RD_SETTING, "enable_planner", False)
    monkeypatch.setattr(router.DS_RD_SETTING, "enable_draft_before_first_sota", True)

    gen = router.ParallelMultiTraceExpGen(scen=None)
    gen.trace_scheduler = DummyScheduler()

    default_exp = DummyExp(name="default_used")
    gen.exp_gen = DummyGen("default", to_return=default_exp)
    gen.draft_exp_gen = DummyGen("draft", to_return=DummyExp("draft"))
    gen.merge_exp_gen = DummyGen("merge", to_return=DummyExp("merge"))

    monkeypatch.setattr(router.logger, "info", lambda *a, **k: None)
    monkeypatch.setattr(router.logger, "log_object", lambda *a, **k: None)

    trace = DummyTrace(leaves=[42], sota_exp_to_submit=None, sota_exp_result="some_sota")
    loop = DummyLoop(loop_idx=11, unfinished=0)

    exp = asyncio.run(gen.async_gen(trace, loop))

    assert exp is default_exp
    # selection should have been (-1,) according to the branch for small leaves
    assert exp.local_selection == (-1,) or trace.current_selection == (-1,)
    # registration check
    assert trace.registered and trace.registered[-1][0] is exp and trace.registered[-1][1] == loop.loop_idx
