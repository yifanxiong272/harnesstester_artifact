import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.tools.bundle')
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
        """Bundle.validate_tools should raise when config.yaml is missing."""
        # create a unique temporary directory under the current working directory
        p = Path.cwd() / f"tmp_bundle_test_{id(object())}"
        p.mkdir(exist_ok=False)
        try:
            # construct the model without running validators to avoid pydantic wrapping
            b = Bundle.model_construct(path=p)
            with self.assertRaises(ValueError) as cm:
                # directly call the validator method to exercise the target branch
                b.validate_tools()

            expected = f"Bundle config file '{(p.resolve() / 'config.yaml')}' does not exist."
            self.assertEqual(str(cm.exception), expected)
        finally:
            # cleanup the created directory if it still exists and is empty
            try:
                if p.exists() and not any(p.iterdir()):
                    p.rmdir()
            except Exception:
                pass
