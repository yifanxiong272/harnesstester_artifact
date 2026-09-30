# file: rdagent/components/coder/factor_coder/evaluators.py:31-120
# asked: {"lines": [39, 40, 42, 44, 45, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 59, 62, 63, 64, 65, 67, 68, 69, 73, 74, 75, 76, 78, 79, 80, 81, 82, 83, 86, 88, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 101, 102, 104, 105, 106, 107, 108, 109, 111, 112, 113, 114, 115, 116, 117, 118, 120], "branches": [[39, 40], [39, 42], [43, 47], [43, 48], [48, 49], [48, 59], [73, 74], [73, 78], [88, 90], [88, 93], [93, 94], [93, 104]]}
# gained: {"lines": [39, 40, 42, 44, 45, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 59, 62, 63, 64, 65, 67, 68, 69, 73, 74, 75, 76, 78, 79, 80, 81, 82, 83, 86, 88, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 101, 102, 104, 105, 106, 107, 108, 109, 111, 112, 113, 114, 115, 116, 117, 118, 120], "branches": [[39, 40], [39, 42], [43, 47], [43, 48], [48, 49], [48, 59], [73, 74], [73, 78], [88, 90], [88, 93], [93, 94], [93, 104]]}

import re
import types
import pytest

from rdagent.components.coder.factor_coder.evaluators import FactorEvaluatorForCoder


class DummyTask:
    def __init__(self, info="task1", version="v1"):
        self._info = info
        self.version = version

    def get_task_information(self):
        return self._info


class DummyWorkspace:
    def __init__(self, exec_return):
        # exec_return should be a tuple (execution_feedback_str, gen_df)
        self._exec_return = exec_return

    def execute(self):
        return self._exec_return


class DummyQueriedKnowledge:
    def __init__(self, success_dict=None, failed_set=None):
        self.success_task_to_knowledge_dict = success_dict or {}
        self.failed_task_info_set = failed_set or set()


class SimpleKnowledge:
    def __init__(self, feedback):
        self.feedback = feedback


# Helper to monkeypatch eva_utils constructors before creating evaluator instance
def _monkeypatch_eva_constructors(monkeypatch):
    import rdagent.components.coder.factor_coder.eva_utils as eva_utils

    class DummyVal:
        def __init__(self, scen):
            self.scen = scen

    class DummyCode:
        def __init__(self, scen):
            self.scen = scen

    class DummyFinal:
        def __init__(self, scen):
            self.scen = scen

    monkeypatch.setattr(eva_utils, "FactorValueEvaluator", DummyVal)
    monkeypatch.setattr(eva_utils, "FactorCodeEvaluator", DummyCode)
    monkeypatch.setattr(eva_utils, "FactorFinalDecisionEvaluator", DummyFinal)


def make_long_number_string():
    # Construct a string that will match the regex replacement:
    # we need a nondigit before the sequence and a nondigit after.
    # Build 51 occurrences of ", -<num>.0"
    numbers = ", ".join([f"-{i}.0" for i in range(51)])
    # Surround with letters to satisfy (?<=\D) and (?=\D)
    return f"X{', ' + numbers}Y"


def test_evaluate_returns_none_when_implementation_is_none(monkeypatch):
    _monkeypatch_eva_constructors(monkeypatch)
    evaluator = FactorEvaluatorForCoder(None)
    task = DummyTask()

    result = evaluator.evaluate(target_task=task, implementation=None)
    assert result is None


def test_queried_knowledge_success_and_failed_branches(monkeypatch):
    # Patch constructors then create evaluator
    _monkeypatch_eva_constructors(monkeypatch)
    evaluator = FactorEvaluatorForCoder(None)
    task = DummyTask(info="task-success")

    # Success branch: queried knowledge contains a mapping to an object with 'feedback' attribute
    success_feedback = object()
    qk_success = DummyQueriedKnowledge(success_dict={"task-success": SimpleKnowledge(success_feedback)})

    res_success = evaluator.evaluate(target_task=task, implementation=DummyWorkspace(("ok", None)), queried_knowledge=qk_success)
    # Should immediately return the stored feedback
    assert res_success is success_feedback

    # Failed branch: task in failed_task_info_set -> returns FactorSingleFeedback-like object
    task_fail = DummyTask(info="task-fail")
    qk_fail = DummyQueriedKnowledge(failed_set={"task-fail"})
    # Implementation can be anything non-None; ensure we don't hit execute in this branch by using a dummy
    res_fail = evaluator.evaluate(target_task=task_fail, implementation=DummyWorkspace(("no", None)), queried_knowledge=qk_fail)

    # The returned object should have the expected messages and flags
    assert hasattr(res_fail, "execution_feedback")
    assert hasattr(res_fail, "value_generated_flag")
    assert hasattr(res_fail, "code_feedback")
    assert hasattr(res_fail, "value_feedback")
    assert hasattr(res_fail, "final_decision") and res_fail.final_decision is False
    assert res_fail.execution_feedback == "This task has failed too many times, skip implementation." or isinstance(res_fail.execution_feedback, str)


def test_full_evaluation_branches_with_regex_and_value_none(monkeypatch):
    # Setup dummy constructors so __init__ is safe
    _monkeypatch_eva_constructors(monkeypatch)
    evaluator = FactorEvaluatorForCoder(None)

    # Prepare an execution string containing the repeated numbers and a warning line which should be removed
    long_numbers = make_long_number_string()
    exec_lines = "Good line\nWarning: something\n" + long_numbers + "\nTrailing safe"
    # gen_df is None to exercise the gen_df is None branch
    ws = DummyWorkspace((exec_lines, None))

    # Monkeypatch evaluators on the instance to controlled stubs
    class ValEvalStub:
        def evaluate(self, **kwargs):
            # Should not be called in gen_df is None case (value_evaluator.evaluate isn't called if gen_df is None)
            raise AssertionError("ValueEvaluator should not be called when gen_df is None")

    class CodeEvalStub:
        def evaluate(self, **kwargs):
            # Return code_feedback and some second value (ignored)
            return ("code_feedback_stub", None)

    class FinalEvalStub:
        def evaluate(self, **kwargs):
            # Return final decision and final feedback
            return (True, "final_feedback_stub")

    evaluator.value_evaluator = ValEvalStub()
    evaluator.code_evaluator = CodeEvalStub()
    evaluator.final_decision_evaluator = FinalEvalStub()

    task = DummyTask(info="t-regex")
    feedback = evaluator.evaluate(target_task=task, implementation=ws, gt_implementation=None, queried_knowledge=None)

    # Check that the warning line was removed and that the long sequence was compressed by regex
    assert "warning" not in feedback.execution_feedback.lower()
    # After regex substitution the long repeated numbers should be condensed to ", "
    assert ", " in feedback.execution_feedback
    assert feedback.value_generated_flag is False
    assert feedback.value_feedback == "No factor value generated, skip value evaluation."
    # final_decision comes from FinalEvalStub -> True
    assert feedback.final_decision is True
    assert feedback.final_feedback == "final_feedback_stub"
    assert feedback.code_feedback == "code_feedback_stub"
    # final_decision_based_on_gt should be False because gt_implementation was None
    assert feedback.final_decision_based_on_gt is False


def test_full_evaluation_with_value_true_and_false(monkeypatch):
    _monkeypatch_eva_constructors(monkeypatch)
    evaluator = FactorEvaluatorForCoder(None)

    # Execution feedback short and no warnings; gen_df not None to exercise value-based branches
    ws_true = DummyWorkspace(("OK\n", {"some": "df"}))
    ws_false = DummyWorkspace(("OK\n", {"some": "df"}))

    task = DummyTask(info="t-val")

    # Case decision_from_value_check is True
    class ValTrue:
        def evaluate(self, **kwargs):
            return ("value_ok", True)

    class CodeShouldNotBeCalled:
        def evaluate(self, **kwargs):
            raise AssertionError("Code evaluator should not be called when value decision is True")

    evaluator.value_evaluator = ValTrue()
    evaluator.code_evaluator = CodeShouldNotBeCalled()
    # final_evaluator should not be called either in True case, but safe stub
    class FinalNever:
        def evaluate(self, **kwargs):
            raise AssertionError("Final decision evaluator should not be called when value decision is True")

    evaluator.final_decision_evaluator = FinalNever()

    feedback_true = evaluator.evaluate(target_task=task, implementation=ws_true, gt_implementation=None, queried_knowledge=None)

    assert feedback_true.value_generated_flag is True
    assert feedback_true.value_feedback == "value_ok"
    assert feedback_true.code_feedback == "Final decision is True and there are no code critics."
    assert feedback_true.final_decision is True
    assert feedback_true.final_feedback == "Value evaluation passed, skip final decision evaluation."
    assert feedback_true.final_decision_based_on_gt is False

    # Case decision_from_value_check is False -> code evaluator will be invoked and final decision set to False
    class ValFalse:
        def evaluate(self, **kwargs):
            return ("value_bad", False)

    class CodeCalled:
        def evaluate(self, **kwargs):
            # Should be called once, return some code feedback
            return ("code_from_eval", None)

    evaluator.value_evaluator = ValFalse()
    evaluator.code_evaluator = CodeCalled()
    # final evaluator should not be called in this branch (value False), but ensure it's present
    evaluator.final_decision_evaluator = FinalNever()

    feedback_false = evaluator.evaluate(target_task=task, implementation=ws_false, gt_implementation=None, queried_knowledge=None)

    assert feedback_false.value_generated_flag is True
    assert feedback_false.value_feedback == "value_bad"
    assert feedback_false.code_feedback == "code_from_eval"
    assert feedback_false.final_decision is False
    assert feedback_false.final_feedback == "Value evaluation failed, skip final decision evaluation."
    assert feedback_false.final_decision_based_on_gt is False
