import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.utils.costs')
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
    def test_case_01(self):
        """_mapping_to_dict should return an empty dict for values that are not mappings,
        are not None, and do not expose a model_dump attribute."""
        # primitive that is not a Mapping and has no model_dump
        self.assertEqual(_mapping_to_dict(123), {})

        # a built-in sequence that is not a Mapping and has no model_dump
        self.assertEqual(_mapping_to_dict([1, 2, 3]), {})

        # a plain object without model_dump attribute
        class Plain:
            pass

        self.assertEqual(_mapping_to_dict(Plain()), {})
