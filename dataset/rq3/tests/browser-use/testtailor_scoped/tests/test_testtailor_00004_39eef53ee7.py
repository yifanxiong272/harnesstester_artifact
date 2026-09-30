import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.service')
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
        """Ensure log_response uses module logger when logger is None and logs all sections."""
        from io import StringIO
        import logging

        # Build a minimal AgentOutput with the required fields
        response = AgentOutput(
            thinking='Considering the page and possible actions.',
            evaluation_previous_goal='Success: completed previous goal',
            memory='Found relevant page content.',
            next_goal='Click the primary CTA',
            action=[ActionModel()]  # minimal action list required by schema
        )

        # Capture logs emitted by the module where log_response is defined
        module_logger = logging.getLogger(log_response.__module__)
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.DEBUG)

        # Ensure we capture debug/info logs from that logger only
        prev_level = module_logger.level
        prev_propagate = module_logger.propagate
        module_logger.addHandler(handler)
        module_logger.setLevel(logging.DEBUG)
        module_logger.propagate = False

        try:
            # Call with logger=None to force the function to use logging.getLogger(__name__)
            log_response(response, registry=None, logger=None)
            handler.flush()
            output = stream.getvalue()
        finally:
            module_logger.removeHandler(handler)
            module_logger.setLevel(prev_level)
            module_logger.propagate = prev_propagate

        # Assert that each section was logged
        self.assertIn('💡 Thinking:', output)
        self.assertIn('Considering the page and possible actions.', output)
        # Evaluation should include the eval text and use the success branch emoji/coloring
        self.assertIn('Eval:', output)
        self.assertIn('Success: completed previous goal', output)
        # Memory and next goal lines should be present
        self.assertIn('🧠 Memory:', output)
        self.assertIn('Found relevant page content.', output)
        self.assertIn('🎯 Next goal:', output)
        self.assertIn('Click the primary CTA', output)
