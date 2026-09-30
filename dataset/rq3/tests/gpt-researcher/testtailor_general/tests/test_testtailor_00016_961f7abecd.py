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
        """Ensure _set_doc_path is invoked when REPORT_SOURCE != 'web' and doc_path is set."""
        custom_config = {
            "REPORT_SOURCE": "local",  # not 'web' to trigger _set_doc_path
            "DOC_PATH": "/tmp/gpt_researcher_test_docs",
            "EMBEDDING": "openai:text-embedding-3-large",
            "FAST_LLM": "openai:gpt-4o-mini",
            "SMART_LLM": "openai:gpt-4o-mini",
            "STRATEGIC_LLM": "openai:gpt-4o-mini",
            "RETRIEVER": "tavily",
        }

        # Patch load_config to return our custom config and patch parsing/validation helpers
        with patch("gpt_researcher.config.Config.load_config", return_value=custom_config):
            with patch("gpt_researcher.config.Config.parse_retrievers", return_value=["tavily"]):
                with patch("gpt_researcher.config.Config.parse_embedding", return_value=("openai", "text-embedding-3-large")):
                    with patch("gpt_researcher.config.Config.parse_llm", return_value=("openai", "gpt-4o-mini")):
                        with patch("gpt_researcher.config.Config.validate_doc_path") as mock_validate:
                            # Construct Config which should call _set_doc_path and thus validate_doc_path
                            cfg = Config(config_path="dummy_path")
                            # doc_path should be set from custom_config and validate_doc_path should have been called
                            self.assertEqual(cfg.doc_path, custom_config["DOC_PATH"])
                            mock_validate.assert_called_once()
