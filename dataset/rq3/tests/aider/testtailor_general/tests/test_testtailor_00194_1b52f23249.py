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
    def test_case_XX(self):
        """get_model_info should return an empty dict when the model id is not found."""
        manager = OpenRouterModelManager()
        # Prepare cached content that does not contain the queried model id
        manager.content = {"data": [{"id": "some/other-model"}]}
        # Prevent _ensure_content from attempting to load/update cache
        manager._cache_loaded = True

        result = manager.get_model_info("openrouter/not/present:model")
        self.assertEqual(result, {})
