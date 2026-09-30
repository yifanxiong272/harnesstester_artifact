import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.CoSTEER.evolvable_subjects')
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
        """Test that EvolvingItem initializes Experiment base correctly."""
        # Create a couple of Task instances
        t1 = Task("task_one")
        t2 = Task("task_two", version=2)

        # Instantiate EvolvingItem which calls Experiment.__init__ internally
        ei = EvolvingItem(sub_tasks=[t1, t2])

        # Experiment.__init__ should set sub_tasks correctly
        self.assertEqual(ei.sub_tasks, [t1, t2])

        # sub_workspace_list should be initialized to a list of None with same length as sub_tasks
        self.assertEqual(ei.sub_workspace_list, [None, None])
        self.assertEqual(len(ei.sub_workspace_list), 2)

        # No ground-truth implementations provided, so attribute should be None
        self.assertIsNone(ei.sub_gt_implementations)

        # Other Experiment defaults
        self.assertEqual(list(ei.based_experiments), [])
        self.assertIsNone(ei.experiment_workspace)
        self.assertIsNone(ei.hypothesis)
        self.assertIsNotNone(ei.running_info)
