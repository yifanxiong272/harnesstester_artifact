import asyncio
from collections import defaultdict

import rdagent.scenarios.data_science.proposal.exp_gen.trace_scheduler as ts
from rdagent.scenarios.data_science.proposal.exp_gen.trace_scheduler import BaseScheduler


class FakeTrace:
    def __init__(self, dag_parent, hist, NEW_ROOT):
        # dag_parent: list where elements are either NEW_ROOT sentinel or iterables of parent ids
        self.dag_parent = dag_parent
        self.hist = hist
        self.NEW_ROOT = NEW_ROOT


def _patch_sleep_noop():
    # Patch the module-local asyncio.sleep so BaseScheduler.next does not actually sleep.
    async def _dummy_sleep(_):
        return None

    ts.asyncio.sleep = _dummy_sleep


def test_list_parents_commit_and_increment_round_101():
    """
    - dag_parent contains both NEW_ROOT and a list of parents -> exercises both branches
      in the for loop that decrement uncommited_rec_status.
    - select returns an iterable parents (tuple) -> exercises the branch that increments
      entries per-parent and returns the tuple.
    Assertions:
    - returned parents match expected
    - rec_commit_idx updated to len(hist)
    - uncommited_rec_status values updated as expected (NEW_ROOT decremented only, parents net 0)
    """
    _patch_sleep_noop()

    NEW_ROOT = "NR"
    # dag_parent: first entry is NEW_ROOT sentinel, second entry is a list of parents [5, 6]
    dag_parent = [NEW_ROOT, [5, 6]]
    hist = ["a", "b"]
    trace = FakeTrace(dag_parent=dag_parent, hist=hist, NEW_ROOT=NEW_ROOT)

    class ListParentScheduler(BaseScheduler):
        def select(self, trace_arg):
            # return a tuple of parents to trigger the 'else' increment branch
            return (5, 6)

    scheduler = ListParentScheduler()

    parents = asyncio.run(scheduler.next(trace))

    # Should return the tuple we emitted
    assert parents == (5, 6)

    # rec_commit_idx should be set to len(hist) after processing dag_parent
    assert scheduler.rec_commit_idx == len(hist)

    # uncommited_rec_status: NEW_ROOT was decremented once and never incremented
    assert scheduler.uncommited_rec_status[NEW_ROOT] == -1

    # Parents 5 and 6 were decremented once (during processing) then incremented once (on selection)
    # Net should be zero
    assert scheduler.uncommited_rec_status[5] == 0
    assert scheduler.uncommited_rec_status[6] == 0


def test_select_none_then_new_root_round_101():
    """
    - select returns None first (forcing the loop to hit await asyncio.sleep(1) path),
      then returns trace.NEW_ROOT on the next iteration.
    - This exercises the 'parents is None' path and the branch where parents == NEW_ROOT.
    Assertions:
    - returned parent equals trace.NEW_ROOT
    - uncommited_rec_status for NEW_ROOT ends up at 0 (decrement then increment)
    """
    _patch_sleep_noop()

    NEW_ROOT = object()
    dag_parent = [NEW_ROOT]
    hist = [1]
    trace = FakeTrace(dag_parent=dag_parent, hist=hist, NEW_ROOT=NEW_ROOT)

    class FlakyScheduler(BaseScheduler):
        def __init__(self):
            super().__init__()
            self._calls = 0

        def select(self, trace_arg):
            # first call -> None, second call -> NEW_ROOT
            self._calls += 1
            if self._calls == 1:
                return None
            return trace_arg.NEW_ROOT

    scheduler = FlakyScheduler()

    parents = asyncio.run(scheduler.next(trace))

    # Should return the NEW_ROOT sentinel
    assert parents == NEW_ROOT

    # NEW_ROOT was decremented once (processing dag_parent) then incremented once (selection) -> back to 0
    assert scheduler.uncommited_rec_status[NEW_ROOT] == 0

    # rec_commit_idx advanced to len(hist)
    assert scheduler.rec_commit_idx == len(hist)
