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
        """Verify JSONParser __init__ sets up strategies and add_json_in_prompt correctly"""
        # Instantiate with add_json_in_prompt=True
        parser_true = JSONParser(add_json_in_prompt=True)

        # Basic attributes
        self.assertIsInstance(parser_true.strategies, list)
        self.assertEqual(len(parser_true.strategies), 4)
        self.assertTrue(parser_true.add_json_in_prompt)

        # Ensure the strategies list contains the expected bound methods (by name)
        strategy_names = [getattr(s, "__func__", s).__name__ for s in parser_true.strategies]
        expected = [
            "_direct_parse",
            "_extract_from_code_block",
            "_fix_python_syntax",
            "_extract_with_fix_combined",
        ]
        self.assertEqual(strategy_names, expected)

        # Verify the direct parse strategy accepts valid JSON and returns the original string
        sample_json = '{"ok": true}'
        direct_result = parser_true.strategies[0](sample_json)
        self.assertEqual(direct_result, sample_json)

        # Verify extract-from-code-block strategy extracts the JSON inside a ```json code block
        block_input = "Some text\n```json\n{\"x\": 1}\n```\nother text"
        extracted = parser_true.strategies[1](block_input)
        # _extract_from_code_block returns the inner JSON string (stripped)
        self.assertEqual(extracted, '{"x": 1}')

        # Instantiate with default (add_json_in_prompt should be False)
        parser_default = JSONParser()
        self.assertFalse(parser_default.add_json_in_prompt)
