import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.events.action.message')
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
        """Ensure the deprecated images_urls property returns the underlying image_urls."""
        action = MessageAction(content='test content')

        # By default it should be None
        self.assertIsNone(action.images_urls)

        # Setting the underlying attribute should be reflected by the deprecated property
        action.image_urls = ['http://example.com/1.png', 'http://example.com/2.png']
        self.assertEqual(
            action.images_urls, ['http://example.com/1.png', 'http://example.com/2.png']
        )

        # Using the deprecated setter should update the underlying attribute
        action.images_urls = ['http://example.com/updated.png']
        self.assertEqual(action.image_urls, ['http://example.com/updated.png'])
        self.assertEqual(action.images_urls, ['http://example.com/updated.png'])
