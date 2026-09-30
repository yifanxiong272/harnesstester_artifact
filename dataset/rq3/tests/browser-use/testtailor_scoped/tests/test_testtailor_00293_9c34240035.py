import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.prompts')
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
        """get_ai_step_user_prompt should wrap inputs in the expected tagged format and preserve newlines."""
        query = "List main points"
        stats_summary = "words: 100\nlinks: 2"
        content = "# Heading\nParagraph text."

        expected = (
            "<query>\nList main points\n</query>\n\n"
            "<content_stats>\nwords: 100\nlinks: 2\n</content_stats>\n\n"
            "<webpage_content>\n# Heading\nParagraph text.\n</webpage_content>"
        )

        result = get_ai_step_user_prompt(query, stats_summary, content)
        self.assertEqual(result, expected)
