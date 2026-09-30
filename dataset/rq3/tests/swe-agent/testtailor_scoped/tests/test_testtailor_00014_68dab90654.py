import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.run_single')
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
        """Ensure run_from_config calls RunSingle.from_config and then run() on the returned instance."""
        dummy_config = object()
        mock_instance = unittest.mock.MagicMock()

        with unittest.mock.patch.object(RunSingle, "from_config", return_value=mock_instance) as mock_from:
            run_from_config(dummy_config)

        mock_from.assert_called_once_with(dummy_config)
        mock_instance.run.assert_called_once()
