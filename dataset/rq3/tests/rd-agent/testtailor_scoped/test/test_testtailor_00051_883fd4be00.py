import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.data_science.raw_data_loader.eval')
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
        """Ensure DataLoaderCoSTEEREvaluator uses target_task.get_task_information and returns cached feedback when present."""
        # create a Task and get its task information (this is the target line executed inside evaluate)
        task = Task(name="example_task", version=1, description="desc", user_instructions=None)
        task_info = task.get_task_information()

        # prepare a DataLoaderEvalFeedback instance to be returned by the queried knowledge
        cached_feedback = DataLoaderEvalFeedback(
            execution="cached",
            return_checking="cached",
            code="cached",
            final_decision=True,
        )

        # holder object that mimics stored knowledge with a .feedback attribute
        holder = type("Holder", (), {"feedback": cached_feedback})()

        # build a queried knowledge object and inject the success mapping
        qk = CoSTEERQueriedKnowledgeV2()
        qk.success_task_to_knowledge_dict = {task_info: holder}

        # create an evaluator instance without running its __init__ (to avoid heavy setup)
        evaluator = object.__new__(DataLoaderCoSTEEREvaluator)

        # Call evaluate; because queried_knowledge contains the key, the method should return early with cached feedback
        result = DataLoaderCoSTEEREvaluator.evaluate(
            evaluator,
            target_task=task,
            implementation=None,
            gt_implementation=None,
            queried_knowledge=qk,
        )

        # verify the returned object is exactly the cached feedback
        self.assertIs(result, cached_feedback)
