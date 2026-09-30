import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.data_science.feature.eval')
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
    def test_case_02(self):
        """Call FeatureCoSTEEREvaluator.evaluate and trigger early-return via QueriedKnowledge.success_task_to_knowledge_dict."""
        # create a Task whose get_task_information() will be used as key
        task = Task(name="sample_task", version=1, description="do something", user_instructions=None)

        # prepare a QueriedKnowledge-like object with the success mapping
        qk = QueriedKnowledge()
        success_feedback = "EARLY_RETURN_FEEDBACK"
        # create a simple container with a .feedback attribute
        class _Container:
            def __init__(self, feedback):
                self.feedback = feedback

        qk.success_task_to_knowledge_dict = {task.get_task_information(): _Container(success_feedback)}
        qk.failed_task_info_set = set()

        # create evaluator instance without calling __init__ to avoid heavy setup
        evaluator = FeatureCoSTEEREvaluator.__new__(FeatureCoSTEEREvaluator)

        # Call evaluate; other parameters are not used due to early return
        result = evaluator.evaluate(target_task=task, implementation=None, gt_implementation=None, queried_knowledge=qk)

        # Expect the exact feedback object returned from the mapping
        self.assertEqual(result, success_feedback)
