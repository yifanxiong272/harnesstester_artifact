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
        # prepare objects
        target_task = Task(name="my_task", version=2, description="a test task")
        fb = FBWorkspace()
        # populate workspace file_dict with various files (only .py non-test should be included)
        fb.file_dict = {
            "main.py": "print('hello world')\n",
            "test_main.py": "def test(): pass\n",
            "README.md": "# readme\n",
        }
        feedback = {"score": 10, "note": "looks good"}

        # create CoSTEERKnowledge which should copy the implementation
        k = CoSTEERKnowledge(target_task=target_task, implementation=fb, feedback=feedback)

        # target_task should be assigned (same object)
        self.assertIs(k.target_task, target_task)

        # implementation should be a deep copy (different object) but contain same file_dict contents
        self.assertIsNot(k.implementation, fb)
        self.assertEqual(k.implementation.file_dict, fb.file_dict)

        # modifying original implementation should not affect the copied one
        fb.file_dict["main.py"] = "print('modified')\n"
        self.assertNotEqual(k.implementation.file_dict["main.py"], fb.file_dict["main.py"])
        self.assertEqual(k.implementation.file_dict["main.py"], "print('hello world')\n")

        # feedback should be assigned as-is (same object)
        self.assertIs(k.feedback, feedback)

        # get_implementation_and_feedback_str should include the implementation code (excluding test files)
        info_str = k.get_implementation_and_feedback_str()
        self.assertIn("File Path: main.py", info_str)
        self.assertIn("print('hello world')", info_str)
        # test_main.py should be excluded from all_codes, so its content must not be present
        self.assertNotIn("def test(): pass", info_str)
        # feedback should be present as string
        self.assertIn(str(feedback), info_str)
