import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.inspector_cli')
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
        """Reorder keys specified in `keys`, keep others in original order, ignore unknown keys."""
        d = {'a': 1, 'b': 2, 'c': 3}
        # 'x' does not exist in d and should be ignored; 'b' and 'a' should come first in that order
        keys = ['b', 'x', 'a']
        result = _move_items_top(d, keys)

        expected = {'b': 2, 'a': 1, 'c': 3}
        # order of keys must match expected order
        self.assertEqual(list(result.keys()), list(expected.keys()))
        # mapping must be equal
        self.assertEqual(result, expected)
        # original dict must remain unchanged and order preserved
        self.assertEqual(list(d.keys()), ['a', 'b', 'c'])
        # function should return a new dict object, not the same one
        self.assertIsNot(result, d)

        # also verify behavior when keys list is empty -> order preserved and new dict returned
        result2 = _move_items_top(d, [])
        self.assertEqual(result2, d)
        self.assertEqual(list(result2.keys()), ['a', 'b', 'c'])
        self.assertIsNot(result2, d)
