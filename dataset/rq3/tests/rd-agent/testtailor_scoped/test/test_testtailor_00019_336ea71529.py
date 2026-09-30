import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.CoSTEER.knowledge_management')
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
        """complete the test case here"""
        # Create a real Task instance
        task = Task("example_task", version=3, description="a test task")

        # Create a fake workspace-like object that mimics FBWorkspace's interface
        class FakeWorkspace:
            def __init__(self, file_dict):
                # mimic the FBWorkspace.file_dict attribute
                self.file_dict = dict(file_dict)

            def copy(self):
                # return a copied new instance to simulate FBWorkspace.copy()
                # use dict.copy() to avoid needing deepcopy import
                return FakeWorkspace(self.file_dict.copy())

            @property
            def all_codes(self):
                # mimic the property used by CoSTEERKnowledge.get_implementation_and_feedback_str
                return "FAKE_CODE_CONTENT"

        # prepare original workspace and feedback
        original_ws = FakeWorkspace({"a.py": "print('hello')"})
        feedback_obj = {"comment": "looks good"}

        # Instantiate the object under test
        ks = CoSTEERKnowledge(task, original_ws, feedback_obj)

        # target_task should be the same object passed in (no copy)
        self.assertIs(ks.target_task, task)

        # implementation should be a copy, not the same object
        self.assertIsNot(ks.implementation, original_ws)

        # copied implementation should have same initial content
        self.assertEqual(ks.implementation.file_dict, original_ws.file_dict)

        # mutating the original should not affect the stored copy (copy semantics)
        original_ws.file_dict["new_file.py"] = "print('changed')"
        self.assertNotIn("new_file.py", ks.implementation.file_dict)

        # feedback should be stored as the same object
        self.assertIs(ks.feedback, feedback_obj)

        # get_implementation_and_feedback_str should include both implementation.all_codes and the feedback string
        combined = ks.get_implementation_and_feedback_str()
        self.assertIn("FAKE_CODE_CONTENT", combined)
        self.assertIn(str(feedback_obj), combined)
