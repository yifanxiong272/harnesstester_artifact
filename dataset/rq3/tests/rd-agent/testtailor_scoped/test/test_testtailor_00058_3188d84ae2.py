import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.data_science.ensemble.eval')
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
        """Ensure evaluate reads task information and metric_name, and returns cached feedback from QueriedKnowledge."""
        # create a Task
        task = Task(name="my_task", description="a test task")

        # create a simple self-like object with scen.metric_name
        class Dummy:
            pass

        self_like = Dummy()
        self_like.scen = Dummy()
        self_like.scen.metric_name = "accuracy"

        # prepare QueriedKnowledge with a cached feedback for this task
        qk = QueriedKnowledge()
        holder = Dummy()
        holder.feedback = "CACHED_FEEDBACK"
        qk.success_task_to_knowledge_dict = {task.get_task_information(): holder}

        # Call the unbound method with our fake self; implementation args are unused due to early return
        result = EnsembleCoSTEEREvaluator.evaluate(self_like, task, None, None, queried_knowledge=qk)

        # Assert the returned value is the cached feedback we provided
        self.assertEqual(result, "CACHED_FEEDBACK")
