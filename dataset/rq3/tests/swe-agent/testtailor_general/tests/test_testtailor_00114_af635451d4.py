import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.run')
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
        """Ensure the 'merge-preds' command dispatches to sweagent.run.merge_predictions.run_from_cli"""
        cmd = ["merge-preds", "--alpha", "1", "--beta", "x"]
        with unittest.mock.patch("sweagent.run.merge_predictions.run_from_cli") as mock_run:
            main(cmd)
            mock_run.assert_called_once_with(["--alpha", "1", "--beta", "x"])
