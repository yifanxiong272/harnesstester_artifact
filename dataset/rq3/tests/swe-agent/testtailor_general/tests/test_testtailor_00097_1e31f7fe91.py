import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.agents')
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
        """complete the test case here"""
        expected = "demonstration_template is ignored when put_demos_in_history is True"
        # Prepare a mock logger that records warning calls
        mock_logger = unittest.mock.Mock()
        mock_logger.warning = unittest.mock.Mock()

        # Replace the get_logger used by the warnings validator with our mock
        func_globals = TemplateConfig.warnings.__globals__
        orig_get_logger = func_globals.get("get_logger")
        func_globals["get_logger"] = lambda name, emoji="": mock_logger

        try:
            # Instantiate with the conditions that trigger the target warning
            cfg = TemplateConfig(put_demos_in_history=True, demonstration_template="demo")

            # The model_validator(mode="after") may have been executed during instantiation.
            # If not, call the method explicitly to ensure the branch is hit.
            if not mock_logger.warning.called:
                cfg.warnings()

            # The validator also emits another warning about empty templates, so check that
            # our specific warning was emitted at least once.
            mock_logger.warning.assert_any_call(expected)
        finally:
            # Restore original get_logger to avoid side effects
            if orig_get_logger is None:
                del func_globals["get_logger"]
            else:
                func_globals["get_logger"] = orig_get_logger
