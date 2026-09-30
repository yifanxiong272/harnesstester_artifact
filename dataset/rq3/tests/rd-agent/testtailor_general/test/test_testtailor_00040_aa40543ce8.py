import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.utils.repo.repo_utils')
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
        """Test RepoAnalyzer.__init__ initializes repo_path as a Path and summaries as empty dict."""
        # Use the current directory ('.') so we don't rely on tempfile or other modules.
        analyzer = RepoAnalyzer(".")
        self.assertIsInstance(analyzer.repo_path, Path)
        self.assertEqual(analyzer.repo_path, Path("."))
        self.assertEqual(analyzer.summaries, {})

        # Also ensure passing a Path object works the same way
        analyzer2 = RepoAnalyzer(Path("."))
        self.assertIsInstance(analyzer2.repo_path, Path)
        self.assertEqual(analyzer2.repo_path, Path("."))
        self.assertEqual(analyzer2.summaries, {})
