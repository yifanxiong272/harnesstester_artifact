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
        """Ensure run_from_cli takes sys.argv when args is None and forwards the result of BasicCLI.get_config to run_from_config."""
        argv = ["prog", "arg1", "arg2"]
        # Ensure module docstring exists (run_from_cli asserts __doc__ is not None)
        with patch("sweagent.run.run_single.__doc__", "module doc"):
            with patch.object(sys, "argv", argv):
                mock_cfg = object()
                with patch("sweagent.run.run_single.BasicCLI") as MockBasicCLI:
                    instance = MockBasicCLI.return_value
                    instance.get_config.return_value = mock_cfg
                    with patch("sweagent.run.run_single.run_from_config") as mock_run_from_config:
                        # Call without args to trigger the branch where args is None
                        run_from_cli()
                        # BasicCLI.get_config should be called with sys.argv[1:]
                        instance.get_config.assert_called_once_with(argv[1:])
                        # run_from_config should be called with what get_config returned
                        mock_run_from_config.assert_called_once_with(mock_cfg)
