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
    def test_case_XX(self):
        """When parse_retrievers raises ValueError, Config should default retrievers to ['tavily'] and print a warning."""
        # Ensure environment variable triggers retriever handling
        os.environ["RETRIEVER"] = "invalid_retriever_name"

        # Patch parse_retrievers to raise ValueError to exercise the except branch
        with patch.object(Config, "parse_retrievers", side_effect=ValueError("Invalid retriever(s) found")) as mock_parse:
            with patch("builtins.print") as mock_print:
                cfg = Config(config_path=None)

                # parse_retrievers should have been called with the env value
                mock_parse.assert_called_once_with("invalid_retriever_name")

                # The exception branch should set retrievers to the default value
                self.assertTrue(hasattr(cfg, "retrievers"))
                self.assertEqual(cfg.retrievers, ["tavily"])

                # A warning print should have been emitted with the expected message fragment
                mock_print.assert_called_with("Warning: Invalid retriever(s) found. Defaulting to 'tavily' retriever.")

        # Clean up environment
        del os.environ["RETRIEVER"]
