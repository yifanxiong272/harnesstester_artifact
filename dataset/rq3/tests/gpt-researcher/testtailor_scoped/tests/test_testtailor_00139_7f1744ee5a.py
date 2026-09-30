import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.config.config')
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
    @patch('gpt_researcher.config.Config.load_config')
    @patch('gpt_researcher.config.Config.parse_retrievers')
    def test_case_XX(self, mock_parse_retrievers, mock_load_config):
        """When parse_retrievers raises ValueError, Config should default retrievers to ['tavily'] and print a warning."""
        # Prepare a minimal config to avoid triggering other code paths (skip doc path handling by using REPORT_SOURCE='web')
        mock_load_config.return_value = {
            "RETRIEVER": "invalid_retriever",
            "EMBEDDING": None,
            "FAST_LLM": None,
            "SMART_LLM": None,
            "STRATEGIC_LLM": None,
            "REPORT_SOURCE": "web",
        }

        # Make parse_retrievers raise ValueError to exercise the except branch
        mock_parse_retrievers.side_effect = ValueError("Invalid retriever(s) found: invalid_retriever")

        # Capture stdout to verify the warning message
        import io, sys
        from gpt_researcher.config import Config

        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            cfg = Config()
        finally:
            sys.stdout = old_stdout

        output = captured.getvalue()
        self.assertIn("Warning: Invalid retriever(s) found: invalid_retriever. Defaulting to 'tavily' retriever.", output)
        self.assertEqual(cfg.retrievers, ["tavily"])
