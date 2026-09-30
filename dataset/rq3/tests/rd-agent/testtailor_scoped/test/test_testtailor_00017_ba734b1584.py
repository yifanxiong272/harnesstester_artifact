import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.oai.backend.base')
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
        """Verify JSONParser initializes strategies in the expected order and sets add_json_in_prompt correctly."""
        # Default initialization: add_json_in_prompt should be False
        parser_default = JSONParser()
        self.assertFalse(parser_default.add_json_in_prompt)
        self.assertIsInstance(parser_default.strategies, list)
        self.assertTrue(all(callable(s) for s in parser_default.strategies))

        expected_names = [
            "_direct_parse",
            "_extract_from_code_block",
            "_fix_python_syntax",
            "_extract_with_fix_combined",
        ]

        actual_names = [
            (s.__func__.__name__ if hasattr(s, "__func__") else s.__name__) for s in parser_default.strategies
        ]
        self.assertEqual(actual_names, expected_names)

        # Explicit True initialization
        parser_true = JSONParser(add_json_in_prompt=True)
        self.assertTrue(parser_true.add_json_in_prompt)
        actual_names_true = [
            (s.__func__.__name__ if hasattr(s, "__func__") else s.__name__) for s in parser_true.strategies
        ]
        self.assertEqual(actual_names_true, expected_names)
        self.assertTrue(all(callable(s) for s in parser_true.strategies))
