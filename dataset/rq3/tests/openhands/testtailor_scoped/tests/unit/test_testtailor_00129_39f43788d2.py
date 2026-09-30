import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.events.serialization.utils')
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
        """Ensure remove_fields deletes matching keys from dicts (including nested dicts/lists)."""
        # prepare a nested structure containing the key to be removed at multiple levels
        obj = {
            'remove_me': 123,
            'keep_top': 'value',
            'nested': {
                'remove_me': 'nested_value',
                'keep_nested': 42,
            },
            'list_of_dicts': [
                {'remove_me': 0, 'keep_in_list': True},
                {'other': 'present'},
            ],
        }
        fields = {'remove_me'}

        # Call the function under test
        remove_fields(obj, fields)

        # Top-level key removed
        self.assertNotIn('remove_me', obj)
        # Other top-level keys remain
        self.assertIn('keep_top', obj)
        self.assertEqual(obj['keep_top'], 'value')

        # Nested dict key removed, other nested keys remain
        self.assertNotIn('remove_me', obj['nested'])
        self.assertIn('keep_nested', obj['nested'])
        self.assertEqual(obj['nested']['keep_nested'], 42)

        # Keys inside list of dicts are removed where present
        self.assertNotIn('remove_me', obj['list_of_dicts'][0])
        self.assertIn('keep_in_list', obj['list_of_dicts'][0])
        self.assertTrue(obj['list_of_dicts'][0]['keep_in_list'])
        # Unrelated dict in the list remains untouched
        self.assertIn('other', obj['list_of_dicts'][1])
        self.assertEqual(obj['list_of_dicts'][1]['other'], 'present')
