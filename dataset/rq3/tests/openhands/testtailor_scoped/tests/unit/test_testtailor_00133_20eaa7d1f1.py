import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.events.observation.commands')
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
    def test_ps1_exit_code_parse_failure(self):
        """When exit_code is present but not parseable, it should be set to -1."""
        ps1_str = r"""###PS1JSON###
{
  "exit_code": "not-a-number",
  "pid": "42",
  "username": "tester"
}
###PS1END###
"""
        matches = CmdOutputMetadata.matches_ps1_metadata(ps1_str)
        self.assertEqual(len(matches), 1)
        metadata = CmdOutputMetadata.from_ps1_match(matches[0])
        # exit_code parsing should fail and be set to -1
        self.assertEqual(metadata.exit_code, -1)
        # pid should still parse correctly from the string "42"
        self.assertEqual(metadata.pid, 42)
        # other fields should be preserved
        self.assertEqual(metadata.username, "tester")
