import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.events.serialization.observation')
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
        """Ensure that when metadata is a dict, it's updated in-place via dict.update(**kwargs)."""
        # Start with a dict representing metadata
        metadata = {
            'exit_code': 0,
            'pid': -1,
            'username': None,
            'hostname': None,
            'prefix': '',
            'suffix': '',
        }

        # Call the function under test with several kwargs (including a new key)
        result = _update_cmd_output_metadata(
            metadata,
            exit_code=2,
            pid=4242,
            username='alice',
            new_field='added',
        )

        # The function should return the same dict object (updated in place)
        self.assertIs(result, metadata)
        self.assertIsInstance(result, dict)

        # Check that existing fields were updated
        self.assertEqual(metadata['exit_code'], 2)
        self.assertEqual(metadata['pid'], 4242)
        self.assertEqual(metadata['username'], 'alice')

        # Check that a new key was added
        self.assertIn('new_field', metadata)
        self.assertEqual(metadata['new_field'], 'added')

        # Further update to ensure update overwrites prior values
        _update_cmd_output_metadata(metadata, exit_code=-1, prefix='>>')
        self.assertEqual(metadata['exit_code'], -1)
        self.assertEqual(metadata['prefix'], '>>')
