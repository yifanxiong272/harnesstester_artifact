import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.tokens.service')
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
        """When CONFIG.XDG_CACHE_HOME is unset or not absolute, xdg_cache_home() returns Path.home()/.cache"""
        old = getattr(CONFIG, 'XDG_CACHE_HOME', None)
        try:
            # Case 1: unset / None -> should return default
            CONFIG.XDG_CACHE_HOME = None
            expected = Path.home() / '.cache'
            result = xdg_cache_home()
            self.assertEqual(result, expected)

            # Case 2: set to a relative path -> should still return default
            CONFIG.XDG_CACHE_HOME = 'relative/path'
            result = xdg_cache_home()
            self.assertEqual(result, expected)
        finally:
            CONFIG.XDG_CACHE_HOME = old
