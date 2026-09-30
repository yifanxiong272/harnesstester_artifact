import pytest

from rdagent.components.coder.factor_coder.evaluators import FactorEvaluatorForCoder


class DummyTask:
    def __init__(self, info, version="v1"):
        self._info = info
        self.version = version

    def get_task_information(self):
        return self._info


class DummyWorkspace:
    def __init__(self, exec_ret):
        # exec_ret should be a tuple (execution_feedback, gen_df)
        self._exec_ret = exec_ret

    def execute(self):
        return self._exec_ret


class SimpleQueriedKnowledge:
    def __init__(self, success_map=None, failed_set=None):
        self.success_task_to_knowledge_dict = success_map or {}
        self.failed_task_info_set = failed_set or set()


class DummyValueEvaluator:
    def __init__(self, ret):
        # ret is (value_feedback, decision_bool_or_none)
        self._ret = ret

    def evaluate(self, *, implementation, gt_implementation, version):
        # signature must match call site
        return self._ret


class DummyCodeEvaluator:
    def __init__(self, ret):
        # ret is (code_feedback, other)
        self._ret = ret

    def evaluate(self, **kwargs):
        return self._ret


class DummyFinalDecisionEvaluator:
    def __init__(self, ret):
        # ret is (final_decision, final_feedback)
        self._ret = ret

    def evaluate(self, **kwargs):
        return self._ret


def make_evaluator_with_mocks(value_ret=None, code_ret=("CODE_OK", None), final_ret=(False, "FINAL_OK")):
    # Create instance without calling __init__ to avoid CoSTEEREvaluator.__init__ requirements
    ev = object.__new__(FactorEvaluatorForCoder)
    # Provide a minimal scen attribute (some code paths may inspect this; set to None)
    ev.scen = None
    # Inject deterministic mock evaluators
    ev.value_evaluator = DummyValueEvaluator(value_ret)
    ev.code_evaluator = DummyCodeEvaluator(code_ret)
    ev.final_decision_evaluator = DummyFinalDecisionEvaluator(final_ret)
    return ev


def test_evaluate_none_implementation_round_069():
    ev = make_evaluator_with_mocks()
    task = DummyTask("t1")
    # implementation is None -> should return None immediately (cover lines ~39-40)
    res = ev.evaluate(target_task=task, implementation=None)
    assert res is None


def test_evaluate_queried_success_round_069():
    ev = make_evaluator_with_mocks()
    task = DummyTask("task-success")

    class K:
        def __init__(self, feedback):
            self.feedback = feedback

    qk = SimpleQueriedKnowledge(success_map={"task-success": K("SUCCESS_FEEDBACK")})
    # implementation must be non-None to avoid the early None return
    impl = DummyWorkspace(("unused", None))
    res = ev.evaluate(target_task=task, implementation=impl, queried_knowledge=qk)
    # Should return the feedback object stored in success map
    assert res == "SUCCESS_FEEDBACK"


def test_evaluate_queried_failed_round_069():
    ev = make_evaluator_with_mocks()
    task = DummyTask("task-failed")
    qk = SimpleQueriedKnowledge(failed_set={"task-failed"})
    impl = DummyWorkspace(("will not be executed", None))
    res = ev.evaluate(target_task=task, implementation=impl, queried_knowledge=qk)
    # The function constructs and returns a FactorSingleFeedback-like object with expected fields
    assert hasattr(res, "execution_feedback")
    assert res.execution_feedback == "This task has failed too many times, skip implementation."
    assert res.code_feedback == "This task has failed too many times, skip code evaluation."
    assert res.value_feedback == "This task has failed too many times, skip value evaluation."
    assert res.value_generated_flag is False
    assert res.final_decision is False
    assert res.final_feedback == "This task has failed too many times, skip final decision evaluation."
    assert res.final_decision_based_on_gt is False


def test_evaluate_gen_df_none_calls_code_and_final_round_069():
    # implementation.execute returns (execution_feedback, None) -> gen_df None branch
    execution_text = "line1\nwarning: ignore this\nline2"
    impl = DummyWorkspace((execution_text, None))

    # value_evaluator return is irrelevant here because gen_df is None; still set to a sentinel
    ev = make_evaluator_with_mocks(value_ret=("SHOULD_NOT_BE_USED", None), code_ret=("CODE_FEEDBACK", None), final_ret=(True, "FINAL_FROM_EVAL"))
    task = DummyTask("task-x")

    res = ev.evaluate(target_task=task, implementation=impl)
    # Ensure execution_feedback filtered out the warning line
    assert "warning" not in (res.execution_feedback or "").lower()
    # line1 and line2 should appear (joined by \n) but without warning line
    assert "line1" in res.execution_feedback
    assert "line2" in res.execution_feedback

    # Because gen_df is None we expect the code_evaluator to be called and its feedback used
    assert res.code_feedback == "CODE_FEEDBACK"
    # final_decision should come from final_decision_evaluator mocked return
    assert res.final_decision is True
    assert res.final_feedback == "FINAL_FROM_EVAL"
    # value_generated_flag should be False in this branch
    assert res.value_generated_flag is False


def test_evaluate_value_true_and_false_branches_round_069():
    # Test value evaluator returning True
    impl_true = DummyWorkspace(("info ok", "gen_df_non_none"))
    ev_true = make_evaluator_with_mocks(value_ret=("VALUE_OK", True))
    t = DummyTask("t-true")
    res_true = ev_true.evaluate(target_task=t, implementation=impl_true)
    # When value evaluator returns True, code feedback is a specific fixed message
    assert res_true.value_generated_flag is True
    assert res_true.value_feedback == "VALUE_OK"
    assert res_true.code_feedback == "Final decision is True and there are no code critics."
    assert res_true.final_decision is True
    assert res_true.final_feedback == "Value evaluation passed, skip final decision evaluation."

    # Test value evaluator returning False
    impl_false = DummyWorkspace(("info ok", "gen_df_non_none"))
    ev_false = make_evaluator_with_mocks(value_ret=("VALUE_BAD", False), code_ret=("CODE_ISSUE", None))
    res_false = ev_false.evaluate(target_task=t, implementation=impl_false)
    assert res_false.value_generated_flag is True
    assert res_false.value_feedback == "VALUE_BAD"
    # code_evaluator return should be used
    assert res_false.code_feedback == "CODE_ISSUE"
    assert res_false.final_decision is False
    assert res_false.final_feedback == "Value evaluation failed, skip final decision evaluation."
