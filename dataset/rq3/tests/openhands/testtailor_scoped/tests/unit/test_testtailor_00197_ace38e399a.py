import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.core.message')
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
        """Ensure Content subclasses that opt into caching get cache_control set to ephemeral."""
        # Create a TextContent instance that requests prompt caching
        tc_cached = TextContent(text='Hello!', cache_prompt=True)

        # Dump the model in 'plain' mode to trigger the @model_serializer(mode='plain')
        dumped = tc_cached.model_dump(mode='plain')

        # The serializer for Content subclasses should produce a dict with cache_control set
        self.assertIsInstance(dumped, dict)
        self.assertIn('cache_control', dumped)
        self.assertEqual(dumped['cache_control'], {'type': 'ephemeral'})

        # Also assert that when caching is not requested, cache_control is not present
        tc_not_cached = TextContent(text='No cache', cache_prompt=False)
        dumped_nc = tc_not_cached.model_dump(mode='plain')
        self.assertIsInstance(dumped_nc, dict)
        self.assertNotIn('cache_control', dumped_nc)
