import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.analytics')
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
        """When the analytics data file exists but contains invalid JSON,
        load_data should catch the JSONDecodeError and call disable(permanently=False).
        """
        # Create a minimal mock "data file" object without relying on external imports
        data_file_mock = type(
            "DF",
            (),
            {
                "exists": lambda self: True,
                # Invalid JSON to trigger json.decoder.JSONDecodeError inside load_data
                "read_text": lambda self: "{ this is not: valid json ",
            },
        )()

        # Create an Analytics instance without running __init__
        inst = Analytics.__new__(Analytics)

        # Ensure attributes that load_data expects exist
        inst.permanently_disable = None
        inst.user_id = None
        inst.asked_opt_in = None

        # Make get_data_file_path return our mocked data file
        inst.get_data_file_path = lambda: data_file_mock

        # Replace disable with a recorder to verify it was called with permanently=False
        recorder = {}

        def disable(permanently):
            recorder["called"] = True
            recorder["permanently"] = permanently

        inst.disable = disable

        # Call the method under test
        inst.load_data()

        # Assert disable was called due to the JSON decode error
        self.assertTrue(recorder.get("called", False), "disable was not called")
        self.assertIn("permanently", recorder, "disable was not called with argument")
        self.assertFalse(recorder["permanently"], "disable should be called with permanently=False")
