import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.base_coder')
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
        """Ensure get_announcements warns when repo-map tokens exceed recommended max."""
        # Create minimal mocked model and io objects
        mock_io = MagicMock()
        mock_io.multiline_mode = False
        mock_io.pretty = False
        # Create a mock main_model with the attributes used by Coder and get_announcements
        mock_model = MagicMock()
        mock_model.weak_model = mock_model  # make weak_model same to avoid "Main model" prefix
        mock_model.name = "test-model"
        mock_model.get_thinking_tokens.return_value = 0
        mock_model.get_reasoning_effort.return_value = 0
        mock_model.info = {"supports_assistant_prefill": False, "max_input_tokens": 0}
        mock_model.caches_by_default = False
        mock_model.streaming = False
        # Provide repo map tokens recommendation
        mock_model.get_repo_map_tokens = MagicMock(return_value=100)

        # Prevent ChatSummary creation inside Coder by passing a dummy summarizer
        dummy_summarizer = MagicMock()

        # Instantiate a Coder without touching git by disabling use_git
        coder = Coder(
            mock_model,
            mock_io,
            use_git=False,
            summarizer=dummy_summarizer,
            fnames=None,
            map_tokens=1024,
        )

        # Ensure the coder has an edit_format for the announcements string
        coder.edit_format = "default"

        # Attach a fake repo_map with a large max_map_tokens and a refresh value
        mock_repo_map = MagicMock()
        mock_repo_map.max_map_tokens = 500
        mock_repo_map.refresh = "auto"
        coder.repo_map = mock_repo_map

        # Ensure main_model.get_repo_map_tokens returns 100 so threshold is 200
        coder.main_model.get_repo_map_tokens = MagicMock(return_value=100)

        lines = coder.get_announcements()
        announcements = "\n".join(lines)

        # Check the repo-map usage line is present
        self.assertIn("Repo-map: using 500 tokens, auto refresh", announcements)

        # Check the warning about excessive map-tokens is present with the computed threshold (100*2=200)
        expected_warning = (
            "Warning: map-tokens > 200 is not recommended. Too much"
            " irrelevant code can confuse LLMs."
        )
        self.assertIn(expected_warning, announcements)
