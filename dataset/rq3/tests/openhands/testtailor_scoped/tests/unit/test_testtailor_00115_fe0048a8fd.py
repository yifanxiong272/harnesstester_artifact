import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.storage.data_models.settings')
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
    def test_api_key_serializer_empty_or_whitespace_returns_none(self):
        """An empty or whitespace-only SecretStr should serialize to None."""
        # Empty secret value
        s_empty = Settings(llm_api_key=SecretStr(''))
        dumped_empty = s_empty.model_dump(mode='json')
        self.assertIn('llm_api_key', dumped_empty)
        self.assertIsNone(dumped_empty['llm_api_key'])

        # Whitespace-only secret value
        s_ws = Settings(llm_api_key=SecretStr('   '))
        dumped_ws = s_ws.model_dump(mode='json')
        self.assertIn('llm_api_key', dumped_ws)
        self.assertIsNone(dumped_ws['llm_api_key'])
