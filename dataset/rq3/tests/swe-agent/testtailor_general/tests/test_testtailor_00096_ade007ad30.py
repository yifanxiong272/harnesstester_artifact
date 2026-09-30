import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.inspector.server')
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
        content = {
            "info": {
                "exit_status": "submitted-v1",
                "submission": {"answer": 42},
            },
            "trajectory": [],
        }

        returned = append_exit(content)

        # The function should return the same object (in-place modification)
        self.assertIs(returned, content)

        # One entry should have been appended to the trajectory
        self.assertEqual(len(content["trajectory"]), 1)

        entry = content["trajectory"][0]
        expected = {
            "thought": "Submitting solution",
            "action": "Model Submission",
            "response": "Submitting solution",
            "observation": content["info"]["submission"],
            "messages": [
                {"role": "system", "content": f"Submission generated - {content['info']['exit_status']}"}
            ],
        }

        self.assertEqual(entry, expected)
