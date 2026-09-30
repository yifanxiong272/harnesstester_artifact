import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.openrouter')
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
    def test_openrouter_get_model_info_returns_empty_when_no_data_key(self):
        """If the cached content exists but lacks a 'data' key, get_model_info should return {}."""
        manager = OpenRouterModelManager()
        # Mark cache as already loaded to prevent network calls in _ensure_content
        manager._cache_loaded = True
        # Provide content that is truthy but does NOT contain a 'data' key
        manager.content = {"version": "1.0", "meta": {"updated": "now"}}

        info = manager.get_model_info("openrouter/some/provider:model")
        self.assertEqual(info, {})
