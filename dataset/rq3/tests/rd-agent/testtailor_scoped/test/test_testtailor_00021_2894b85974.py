import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.data_science.workflow.eval')
except Exception:
    _testtailor_target = None
else:
    globals().update({
        name: value
        for name, value in vars(_testtailor_target).items()
        if not name.startswith("__")
    })

class _TestTailorTimeout:
    @staticmethod
    def timeout(_seconds):
        return lambda function: function

timeout_decorator = _TestTailorTimeout()

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_case_XX(self):
        """Ensure evaluate reads target_task.get_task_information() and returns cached feedback when present in QueriedKnowledge."""
        # create a Task
        task = Task(name="sample_task", description="a short description")

        # prepare a feedback object to be returned via QueriedKnowledge
        cached_fb = WorkflowSingleFeedback(
            execution="cached execution",
            return_checking="cached return checking",
            code="cached code",
            final_decision=True,
        )

        # construct a QueriedKnowledge-like object with the required mapping
        qk = QueriedKnowledge()
        holder = type("Holder", (), {})()
        holder.feedback = cached_fb
        qk.success_task_to_knowledge_dict = {task.get_task_information(): holder}

        # Call the evaluator's method in a way that stops execution at the early return.
        result = WorkflowGeneralCaseSpecEvaluator.evaluate(
            None,  # self is not used before the early return
            target_task=task,
            implementation=None,
            gt_implementation=None,
            queried_knowledge=qk,
        )

        # The returned object should be the same cached feedback we provided.
        self.assertIs(result, cached_fb)
