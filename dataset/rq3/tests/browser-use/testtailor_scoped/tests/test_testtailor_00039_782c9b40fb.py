import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.views')
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
        """Default-branch hashing: excludes None values and is order-insensitive."""
        params1 = {'b': 2, 'a': None, 'c': 'value', 'z': None}
        params2 = {'c': 'value', 'x': None, 'b': 2}
        params3 = {'b': 3, 'c': 'value'}  # different non-None value should change hash
        params4 = {'b': 2, 'c': 'value'}  # same as params1 but without None keys

        h1 = compute_action_hash('custom', params1)
        h2 = compute_action_hash('custom', params2)
        h3 = compute_action_hash('custom', params3)
        h4 = compute_action_hash('custom', params4)

        # None-valued keys and parameter ordering should not affect the resulting hash
        self.assertEqual(h1, h2)
        self.assertEqual(h1, h4)

        # Changing a non-None value should change the hash
        self.assertNotEqual(h1, h3)
