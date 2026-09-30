import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.run_replay')
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
        """Ensure run_from_config calls RunReplay.from_config and then main() on the result."""
        dummy_config = object()
        with unittest.mock.patch.object(RunReplay, "from_config") as mock_from_config:
            main_mock = unittest.mock.MagicMock()
            # Return an object whose .main attribute is our mock
            mock_from_config.return_value = unittest.mock.MagicMock(main=main_mock)

            # Call the function under test
            run_from_config(dummy_config)

            # Verify RunReplay.from_config was called with our config and main() was invoked
            mock_from_config.assert_called_once_with(dummy_config)
            main_mock.assert_called_once()
