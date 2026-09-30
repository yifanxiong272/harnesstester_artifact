import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.args')
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
        """Call get_md_help and assert key markdown sections and env var text appear."""
        help_md = get_md_help()

        # Should return a string
        self.assertIsInstance(help_md, str)

        # Usage should be wrapped in code fences by the formatter
        self.assertIn("```", help_md)

        # Top-level section headings are converted to markdown
        self.assertIn("## API Keys and settings", help_md)

        # The long option should include a metavar (VALUE) in the markdown produced
        self.assertIn("### `--openai-api-key VALUE`", help_md)

        # parse_known_args() should have set up env var names with the AIDER_ prefix
        self.assertIn("Environment variable: `AIDER_OPENAI_API_KEY`", help_md)
