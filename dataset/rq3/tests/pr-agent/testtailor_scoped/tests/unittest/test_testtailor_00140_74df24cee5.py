import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.algo.file_filter')
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
        """Ensure filter_ignored follows the 'bitbucket' branch and builds files_o correctly."""
        # prepare two file-like objects: one that should be kept, one that should be ignored
        f_keep = type("F", (), {})()
        f_keep.new = type("N", (), {"path": "keep.txt"})()
        f_ignore = type("F", (), {})()
        f_ignore.new = type("N", (), {"path": "Readme.md"})()

        # prepare mocked settings returned by get_settings()
        mock_settings = MagicMock()
        mock_settings.ignore = MagicMock()
        # no explicit regex patterns
        mock_settings.ignore.regex = []
        # glob that should match Readme.md
        mock_settings.ignore.glob = ["*.md"]
        mock_settings.config = {"ignore_language_framework": []}
        mock_settings.generated_code = {}

        # Patch the get_settings used inside filter_ignored by injecting into its globals
        orig_get_settings = filter_ignored.__globals__.get("get_settings")
        filter_ignored.__globals__["get_settings"] = lambda: mock_settings
        try:
            result = filter_ignored([f_keep, f_ignore], platform="bitbucket")
        finally:
            # restore original to avoid side effects
            filter_ignored.__globals__["get_settings"] = orig_get_settings

        # the file matching *.md should be filtered out, leaving only f_keep
        assert isinstance(result, list)
        assert len(result) == 1
        assert getattr(result[0].new, "path", None) == "keep.txt"
