# file: rdagent/components/coder/factor_coder/evaluators.py:31-120
# asked: {"lines": [39, 40, 42, 44, 45, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 59, 62, 63, 64, 65, 67, 68, 69, 73, 74, 75, 76, 78, 79, 80, 81, 82, 83, 86, 88, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 101, 102, 104, 105, 106, 107, 108, 109, 111, 112, 113, 114, 115, 116, 117, 118, 120], "branches": [[39, 40], [39, 42], [43, 47], [43, 48], [48, 49], [48, 59], [73, 74], [73, 78], [88, 90], [88, 93], [93, 94], [93, 104]]}
# gained: {"lines": [39, 40, 42, 44, 45, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 59, 62, 63, 64, 65, 67, 68, 69, 73, 74, 75, 76, 78, 79, 80, 81, 82, 83, 86, 88, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 101, 102, 104, 105, 106, 107, 108, 109, 111, 112, 113, 114, 115, 116, 117, 118, 120], "branches": [[39, 40], [39, 42], [43, 47], [43, 48], [48, 49], [48, 59], [73, 74], [73, 78], [88, 90], [88, 93], [93, 94], [93, 104]]}

import re
import types
import pytest

from rdagent.components.coder.factor_coder.evaluators import FactorEvaluatorForCoder


class DummyTask:
    def __init__(self, info, version="v"):
        self._info = info
        self.version = version

    def get_task_information(self):
        return self._info


class DummyWorkspace:
    def __init__(self, execution_return):
        # execution_return should be a tuple (execution_feedback_str, gen_df_or_None)
        self._execution_return = execution_return

    def execute(self):
        return self._execution_return


class DummyQueriedKnowledge:
    def __init__(self, success_map=None, failed_set=None):
        self.success_task_to_knowledge_dict = success_map or {}
        self.failed_task_info_set = failed_set or set()


class ContainerWithFeedback:
    def __init__(self, feedback):
        self.feedback = feedback


def make_long_number_sequence(n=60):
    # produce "x" + ", 1.0, 2.0, ... + "y" so regex will match and replace the long sequence
    nums = ", ".join(f"{float(i):.1f}" for i in range(1, n + 1))
    return "x" + ", " + nums + "y"


def make_evaluator_stub():
    # Create instance without calling original __init__
    ev = object.__new__(FactorEvaluatorForCoder)
    # minimal attributes expected by evaluate
    ev.scen = None
    # default evaluators that can be overridden by tests
    ev.value_evaluator = types.SimpleNamespace(evaluate=lambda **kwargs: ("default_value", None))
    ev.code_evaluator = types.SimpleNamespace(evaluate=lambda **kwargs: ("default_code", None))
    ev.final_decision_evaluator = types.SimpleNamespace(evaluate=lambda **kwargs: (False, "default_final"))
    return ev


def test_evaluate_none_implementation():
    evaluator = make_evaluator_stub()
    task = DummyTask("t_none")
    res = evaluator.evaluate(target_task=task, implementation=None)
    assert res is None


def test_evaluate_with_queried_success_and_failed():
    evaluator = make_evaluator_stub()
    task_succ = DummyTask("succ_task")
    success_container = ContainerWithFeedback(feedback="precomputed_feedback")
    qk = DummyQueriedKnowledge(success_map={"succ_task": success_container}, failed_set={"failed_task"})

    # success path: should return the feedback value (not the container)
    res = evaluator.evaluate(target_task=task_succ, implementation=DummyWorkspace(("ok", None)), queried_knowledge=qk)
    assert res == "precomputed_feedback"

    # failed path: returns a FactorSingleFeedback-like object with set fields
    task_fail = DummyTask("failed_task")
    res2 = evaluator.evaluate(target_task=task_fail, implementation=DummyWorkspace(("ok", None)), queried_knowledge=qk)
    assert hasattr(res2, "execution_feedback")
    assert res2.execution_feedback == "This task has failed too many times, skip implementation."
    assert res2.value_generated_flag is False
    assert res2.code_feedback == "This task has failed too many times, skip code evaluation."
    assert res2.value_feedback == "This task has failed too many times, skip value evaluation."
    assert res2.final_decision is False
    assert res2.final_feedback == "This task has failed too many times, skip final decision evaluation."
    assert res2.final_decision_based_on_gt is False


def test_evaluate_gen_df_none_calls_code_and_final_decision():
    evaluator = make_evaluator_stub()

    # Create execution feedback that includes a long sequence to trigger regex replacement
    long_seq = make_long_number_sequence(60)
    # also include some warning lines to ensure they get filtered out
    multi_line_exec = "Line ok\nWarning: something\n" + long_seq + "\nAnother line"
    workspace = DummyWorkspace((multi_line_exec, None))  # gen_df is None

    task = DummyTask("task_gennone")

    # stub out evaluators
    called = {"code": False, "final": False, "value": False}

    class StubCodeEvaluator:
        def evaluate(self, **kwargs):
            called["code"] = True
            # returns (code_feedback, extra)
            return "code_feedback_stub", None

    class StubFinalEvaluator:
        def evaluate(self, **kwargs):
            called["final"] = True
            return True, "final_ok"

    evaluator.code_evaluator = StubCodeEvaluator()
    evaluator.final_decision_evaluator = StubFinalEvaluator()
    # ensure value evaluator exists but should not be called since gen_df is None
    class StubValueEvaluator:
        def evaluate(self, **kwargs):
            called["value"] = True
            return "value", True

    evaluator.value_evaluator = StubValueEvaluator()

    # pass a non-None gt_implementation to set final_decision_based_on_gt True
    gt_impl = object()
    res = evaluator.evaluate(target_task=task, implementation=workspace, gt_implementation=gt_impl, queried_knowledge=None)

    # verify code and final evaluator were called, value evaluator not called
    assert called["code"] is True
    assert called["final"] is True
    assert called["value"] is False

    # verify returned feedback content
    assert hasattr(res, "execution_feedback")
    # the long sequence should have been replaced (i.e., not contain the full numeric sequence)
    assert "warning" not in res.execution_feedback.lower()
    assert res.value_generated_flag is False
    assert res.code_feedback == "code_feedback_stub"
    assert res.final_decision is True
    assert res.final_feedback == "final_ok"
    assert res.final_decision_based_on_gt is True


def test_evaluate_value_true_and_false_branches():
    evaluator = make_evaluator_stub()
    task = DummyTask("task_val")

    # common execution feedback without warnings and with short numbers so regex won't change it
    exec_feedback = "start\nok\nend"

    # CASE 1: value evaluator returns True => code evaluator should NOT be called
    workspace1 = DummyWorkspace((exec_feedback, {"some": "df"}))  # gen_df not None

    called = {"code": False}

    class ValueTrueEvaluator:
        def evaluate(self, **kwargs):
            return "value_ok", True

    class CodeShouldNotBeCalled:
        def evaluate(self, **kwargs):
            called["code"] = True
            return "should_not", None

    evaluator.value_evaluator = ValueTrueEvaluator()
    evaluator.code_evaluator = CodeShouldNotBeCalled()
    evaluator.final_decision_evaluator = types.SimpleNamespace(evaluate=lambda **kwargs: (_ for _ in ()).throw(AssertionError("final decision should not be called in value-True case")))

    res1 = evaluator.evaluate(target_task=task, implementation=workspace1, gt_implementation=None, queried_knowledge=None)
    assert res1.value_generated_flag is True
    assert res1.value_feedback == "value_ok"
    assert res1.code_feedback == "Final decision is True and there are no code critics."
    assert res1.final_decision is True
    assert "Value evaluation passed" in res1.final_feedback
    assert called["code"] is False
    assert res1.final_decision_based_on_gt is False

    # CASE 2: value evaluator returns False => code evaluator SHOULD be called and final evaluation skipped
    workspace2 = DummyWorkspace((exec_feedback, {"some": "df"}))
    called2 = {"code": False}

    class ValueFalseEvaluator:
        def evaluate(self, **kwargs):
            return "value_bad", False

    class CodeEvaluatorCalled:
        def evaluate(self, **kwargs):
            called2["code"] = True
            return "code_after_value", None

    evaluator.value_evaluator = ValueFalseEvaluator()
    evaluator.code_evaluator = CodeEvaluatorCalled()
    # final decision evaluator should not be called in this branch (they set final_decision directly)
    evaluator.final_decision_evaluator = types.SimpleNamespace(evaluate=lambda **kwargs: (_ for _ in ()).throw(AssertionError("final decision should not be called in value-False case")))
    res2 = evaluator.evaluate(target_task=task, implementation=workspace2, gt_implementation=None, queried_knowledge=None)
    assert res2.value_generated_flag is True
    assert res2.value_feedback == "value_bad"
    assert called2["code"] is True
    assert res2.code_feedback == "code_after_value"
    assert res2.final_decision is False
    assert "Value evaluation failed" in res2.final_feedback
    assert res2.final_decision_based_on_gt is False
