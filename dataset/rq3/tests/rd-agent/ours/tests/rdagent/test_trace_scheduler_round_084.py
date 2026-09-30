import types
import pytest

from rdagent.scenarios.data_science.proposal.exp_gen.trace_scheduler import MCTSScheduler


class DummyTrace:
    """Minimal stand-in for DSTrace used by MCTSScheduler.select tests.

    Attributes used by the tested code:
    - sub_trace_count: int
    - hist: list (used only for len(hist) to produce leaf indices)
    - NEW_ROOT: int (key used to index uncommited_rec_status)
    """

    NEW_ROOT = -1

    def __init__(self, hist, sub_trace_count=0):
        self.hist = hist
        self.sub_trace_count = sub_trace_count


def make_scheduler(max_trace_num=1, temperature=1.0):
    # MCTSScheduler inherits a constructor taking (max_trace_num, temperature, ...)
    sched = MCTSScheduler(max_trace_num, temperature)
    # Ensure required internal structures exist and are deterministic for tests
    sched.uncommited_rec_status = {}
    sched.node_prior = {}
    sched.global_visit_count = 0
    return sched


def test_select_returns_new_root_round_084():
    sched = make_scheduler(max_trace_num=1)
    trace = DummyTrace(hist=[0, 1], sub_trace_count=0)
    # ensure uncommitted count at NEW_ROOT makes the first branch true
    sched.uncommited_rec_status[trace.NEW_ROOT] = 0

    res = sched.select(trace)

    # When the first branch is taken, the function returns the NEW_ROOT value directly
    assert res == trace.NEW_ROOT


def test_select_returns_none_when_no_leaves_round_084():
    # Case where available_leaves is empty -> select should return None
    sched = make_scheduler(max_trace_num=0)
    trace = DummyTrace(hist=[], sub_trace_count=0)
    # Make first-branch false so execution continues to available_leaves check
    sched.uncommited_rec_status[trace.NEW_ROOT] = 0

    res = sched.select(trace)
    assert res is None


def test_select_raises_on_negative_potential_round_084():
    # If any potential is negative, select should raise ValueError
    sched = make_scheduler(max_trace_num=0)
    trace = DummyTrace(hist=[0], sub_trace_count=0)
    sched.uncommited_rec_status[trace.NEW_ROOT] = 0

    # Patch calculate_potential to return a negative potential for the single leaf
    def neg_potential(_trace, leaf):
        return -0.5

    sched.calculate_potential = types.MethodType(lambda self, t, l: neg_potential(t, l), sched)

    with pytest.raises(ValueError) as excinfo:
        sched.select(trace)
    assert "Potential function returned a negative value." in str(excinfo.value)


def test_select_sets_priors_and_selects_best_leaf_round_084():
    # Test the normal selection path: priors set, best leaf chosen based on q+u, global_visit_count incremented
    sched = make_scheduler(max_trace_num=0)
    trace = DummyTrace(hist=[0, 1], sub_trace_count=0)
    sched.uncommited_rec_status[trace.NEW_ROOT] = 0

    # Patch calculate_potential to return non-negative values (not used because we patch softmax)
    sched.calculate_potential = types.MethodType(lambda self, t, l: 1.0 + float(l), sched)

    # Force deterministic priors from the softmax step
    def fake_softmax(potentials):
        # Return a specific, valid probability distribution matching number of leaves
        assert len(potentials) == 2
        return [0.4, 0.6]

    sched._softmax_probabilities = types.MethodType(lambda self, p: fake_softmax(p), sched)

    # Make _get_q and _get_u deterministic so leaf 1 has higher q+u
    def get_q(node_id):
        return 0.0 if node_id == 0 else 0.2

    def get_u(node_id):
        return 0.1 if node_id == 0 else 0.3

    sched._get_q = types.MethodType(lambda self, n: get_q(n), sched)
    sched._get_u = types.MethodType(lambda self, n: get_u(n), sched)

    # start with known visit count
    sched.global_visit_count = 5

    res = sched.select(trace)

    # Priors should have been written into node_prior for both leaves
    assert pytest.approx(sched.node_prior[0], rel=1e-6) == 0.4
    assert pytest.approx(sched.node_prior[1], rel=1e-6) == 0.6

    # Best leaf should be 1 (higher q+u), returned as a 1-tuple
    assert res == (1,)

    # global_visit_count should have been incremented by 1
    assert sched.global_visit_count == 6
