import types
from types import SimpleNamespace
import pytest

from rdagent.scenarios.data_science.proposal.exp_gen import base
from rdagent.scenarios.data_science.proposal.exp_gen.base import DSTrace


def _make_expr(component, decision_value=None):
    """Helper to create a fake experiment and feedback pair.

    - experiment: has .hypothesis.component
    - feedback: None or object with .decision attribute
    """
    exp = SimpleNamespace(hypothesis=SimpleNamespace(component=component))
    fb = None if decision_value is None else SimpleNamespace(decision=decision_value)
    return exp, fb


def test_sota_and_failed_and_max_retrieve_round_079():
    # Arrange: force coder_on_whole_pipeline True so has_final_component starts True
    monkey = types.SimpleNamespace(coder_on_whole_pipeline=True)
    # Patch the module-level DS_RD_SETTING to the simple namespace
    base.DS_RD_SETTING = monkey

    # Set COMPLETE_ORDER on the DSTrace class so final_component is predictable
    DSTrace.COMPLETE_ORDER = ["comp1", "comp2", "FINAL"]

    # Build a search list that will produce: failed -> sota (resets fail) -> failed after sota
    exp1, fb1 = _make_expr("X", decision_value=False)   # becomes failed_list [exp1]
    exp2, fb2 = _make_expr("Y", decision_value=True)    # becomes SOTA [exp2], failed reset []
    exp3, fb3 = _make_expr("FINAL", decision_value=False)  # appended to failed_list after sota

    search_list = [(exp1, fb1), (exp2, fb2), (exp3, fb3)]

    # Create a real DSTrace instance and override its retrieve_search_list to return our list
    inst = DSTrace(None, None)
    inst.retrieve_search_list = lambda search_type, selection=None: search_list

    # Act: request at most 1 of each via max_retrieve_num and return all combined
    result_all = inst.experiment_and_feedback_list_after_init(
        return_type="all", search_type="any", selection=None, max_retrieve_num=1
    )

    # Assert: we expect the last SOTA (exp2) then the last failed (exp3)
    assert isinstance(result_all, list)
    assert len(result_all) == 2
    # check the SOTA element first
    assert result_all[0][0].hypothesis.component == "Y"
    assert result_all[0][1].decision is True
    # check the failed element second
    assert result_all[1][0].hypothesis.component == "FINAL"
    assert result_all[1][1].decision is False

    # Also assert direct 'sota' return type returns only the SOTA list (no slicing applied here)
    result_sota = inst.experiment_and_feedback_list_after_init(
        return_type="sota", search_type="any", selection=None, max_retrieve_num=None
    )
    assert result_sota == [(exp2, fb2)]


def test_without_initial_has_final_component_and_invalid_return_round_079():
    # Arrange: coder_on_whole_pipeline False so has_final_component starts False
    base.DS_RD_SETTING = types.SimpleNamespace(coder_on_whole_pipeline=False)

    # final component name
    DSTrace.COMPLETE_ORDER = ["FINAL"]

    # Build a search list where the first item sets has_final_component via the component check
    # but is NOT processed by the inner decision branch because has_final_component was False
    exp1, fb1 = _make_expr("FINAL", decision_value=True)   # will set has_final_component but not be added
    exp2, fb2 = _make_expr("FINAL", decision_value=True)   # will be processed and added to SOTA
    exp3, fb3 = _make_expr("OTHER", decision_value=False)  # will become failed_list after

    search_list = [(exp1, fb1), (exp2, fb2), (exp3, fb3)]

    inst = DSTrace(None, None)
    inst.retrieve_search_list = lambda search_type, selection=None: search_list

    # Act + Assert: 'sota' should return only the second experiment (exp2)
    res_sota = inst.experiment_and_feedback_list_after_init(
        return_type="sota", search_type="any", selection=None, max_retrieve_num=None
    )
    assert res_sota == [(exp2, fb2)]

    # 'failed' should return the failed list (exp3)
    res_failed = inst.experiment_and_feedback_list_after_init(
        return_type="failed", search_type="any", selection=None, max_retrieve_num=None
    )
    assert res_failed == [(exp3, fb3)]

    # invalid return_type should raise ValueError
    with pytest.raises(ValueError):
        inst.experiment_and_feedback_list_after_init(
            return_type="invalid", search_type="any", selection=None, max_retrieve_num=None
        )
