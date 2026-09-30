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
        """Ensure that when entry role is 'tool' the content[0].cache_control is removed
        and a top-level cache_control is set to ephemeral."""
        # prepare an entry where content is a list and content[0] has a cache_control
        entry = {
            "role": "tool",
            "content": [
                {
                    "type": "text",
                    "text": "sample",
                    "cache_control": {"type": "persistent"},
                }
            ],
        }

        # sanity check before calling the function under test
        self.assertIsInstance(entry["content"], list)
        self.assertIn("cache_control", entry["content"][0])

        # call the function under test (imported elsewhere in the test module)
        _set_cache_control(entry)

        # after calling, content[0] should no longer have cache_control
        self.assertNotIn("cache_control", entry["content"][0])
        # and the entry itself should have a top-level ephemeral cache_control
        self.assertIn("cache_control", entry)
        self.assertEqual(entry["cache_control"], {"type": "ephemeral"})
