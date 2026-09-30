import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.utils.env')
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
        """Test that cleanup_container logs a warning when stop() or remove() raises."""
        logger_path = "rdagent.utils.env.logger"

        # Case 1: stop() raises -> should log the stop error
        with unittest.mock.patch(logger_path) as mock_logger:
            mock_container = unittest.mock.Mock()
            mock_container.id = "fakeid"
            mock_container.stop.side_effect = Exception("stop failed")
            # remove() should not be reached, but define it anyway
            mock_container.remove.return_value = None

            cleanup_container(mock_container, context="testctx")

            expected_msg = "Failed to cleanup testctx container fakeid: stop failed"
            mock_logger.warning.assert_called_once_with(expected_msg)

        # Case 2: stop() succeeds but remove() raises -> should log the remove error
        with unittest.mock.patch(logger_path) as mock_logger:
            mock_container = unittest.mock.Mock()
            mock_container.id = "anotherid"
            mock_container.stop.return_value = None
            mock_container.remove.side_effect = Exception("remove failed")

            cleanup_container(mock_container, context="")

            expected_msg = "Failed to cleanup container anotherid: remove failed"
            mock_logger.warning.assert_called_once_with(expected_msg)
