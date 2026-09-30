import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.history_processors')
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
        """When entry role is 'tool', cache_control is moved from content[0] to entry['cache_control']."""
        # Prepare a HistoryItem-like dict with content as a list and role 'tool'
        entry = {
            "role": "tool",
            "content": [
                {
                    "type": "text",
                    "text": "sample",
                    "cache_control": {"type": "transient"},
                }
            ],
        }

        # Call the function under test
        _set_cache_control(entry)

        # After calling, the content[0] should no longer have cache_control
        self.assertNotIn("cache_control", entry["content"][0])
        # And the entry should have a top-level cache_control set to ephemeral
        self.assertIn("cache_control", entry)
        self.assertEqual(entry["cache_control"], {"type": "ephemeral"})
