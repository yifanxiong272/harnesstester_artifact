import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.reviewer')
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
        """Verify to_format_dict copies self.info and formats keys,
        adding a missing 'submission' entry as an empty string."""
        # Create a minimal dummy object with an `info` attribute but NOT a ReviewSubmission instance.
        dummy = type("Dummy", (), {})()
        # info has a string entry and a dict entry; deliberately omit "submission"
        dummy.info = {"foo": "bar", "meta": {"a": "A"}}

        # Call the class method unbound, passing our dummy as self.
        result = ReviewSubmission.to_format_dict(dummy)

        # Expect the dict to contain flattened keys and a filled-in submission key.
        expected = {"foo": "bar", "meta_a": "A", "submission": ""}
        self.assertEqual(result, expected)

        # Ensure the original dummy.info was not mutated (copy.deepcopy used).
        self.assertNotIn("submission", dummy.info)
