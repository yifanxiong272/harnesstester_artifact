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
        """Ensure string glob patterns from generated_code are treated as a single-item list."""
        # Build a minimal settings object that filter_ignored will consume via get_settings()
        class _Ignore:
            pass

        ignore = _Ignore()
        ignore.regex = []
        ignore.glob = []

        settings = type("S", (), {})()
        settings.ignore = ignore
        # Ensure the loop over code_generators runs
        settings.config = {'ignore_language_framework': ['mygen']}
        # Provide a string (not a list) for generated_code['mygen'] to trigger the branch
        settings.generated_code = {'mygen': '**/*.gen'}

        # Inject a stub get_settings into filter_ignored's globals so it returns our settings
        orig_get_settings = filter_ignored.__globals__.get('get_settings')
        filter_ignored.__globals__['get_settings'] = lambda: settings

        try:
            files = [
                type('', (object,), {'filename': 'keep.txt'})(),
                type('', (object,), {'filename': 'ignore.gen'})(),
                type('', (object,), {'filename': 'sub/another.gen'})(),
                type('', (object,), {'filename': 'script.py'})(),
            ]

            expected = [files[0], files[3]]

            filtered = filter_ignored(files)
            self.assertEqual(
                filtered,
                expected,
                f"Expected {[f.filename for f in expected]}, got {[f.filename for f in filtered]}"
            )
        finally:
            # restore original get_settings to avoid side effects
            if orig_get_settings is None:
                filter_ignored.__globals__.pop('get_settings', None)
            else:
                filter_ignored.__globals__['get_settings'] = orig_get_settings
