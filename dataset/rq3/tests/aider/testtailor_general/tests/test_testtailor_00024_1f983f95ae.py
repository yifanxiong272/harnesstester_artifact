import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.single_wholefile_func_coder')
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
        """Ensure SingleWholeFileFunctionCoder sets gpt_prompts and calls super().__init__"""
        base_cls = SingleWholeFileFunctionCoder.__mro__[1]

        # Replace the base class __init__ with a simple recorder function so we don't run real init
        def fake_init(self, *a, **kw):
            self._super_init_args = a
            self._super_init_kwargs = kw

        with patch.object(base_cls, "__init__", new=fake_init):
            obj = SingleWholeFileFunctionCoder(1, 2, sample="x")

            # subclass __init__ should set gpt_prompts
            self.assertIsInstance(obj.gpt_prompts, SingleWholeFileFunctionPrompts)

            # and the fake super __init__ should have recorded the forwarded args/kwargs
            self.assertTrue(hasattr(obj, "_super_init_args"))
            self.assertEqual(obj._super_init_args, (1, 2))
            self.assertEqual(obj._super_init_kwargs, {"sample": "x"})
