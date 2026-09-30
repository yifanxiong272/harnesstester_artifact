import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.mcp.server')
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
        """When no stderr handler exists on the root logger, _ensure_all_loggers_use_stderr
        must create a StreamHandler writing to sys.stderr with the expected formatter and
        must configure the root logger and all existing loggers to use it with CRITICAL level
        and propagation disabled.
        """
        # Import modules dynamically to avoid top-level import statements in this snippet.
        logging = __import__('logging')
        sys = __import__('sys')
        server_mod = __import__('browser_use.mcp.server', fromlist=['*'])
        ensure_fn = getattr(server_mod, '_ensure_all_loggers_use_stderr')

        root = logging.root

        # Snapshot root state
        orig_root_handlers = list(root.handlers)
        orig_root_level = root.level

        # Snapshot existing loggers' state
        manager = root.manager
        orig_logger_states = {}
        for name in list(manager.loggerDict.keys()):
            logger_obj = logging.getLogger(name)
            orig_logger_states[name] = (list(logger_obj.handlers), logger_obj.level, logger_obj.propagate)

        # Prepare environment: ensure root has a handler that is NOT stderr (use stdout)
        root.handlers = [logging.StreamHandler(sys.stdout)]
        root.setLevel(logging.DEBUG)

        # Create a test logger that should be reconfigured by the function
        test_logger = logging.getLogger('test.ensure_stderr_logger')
        test_logger.handlers = [logging.StreamHandler(sys.stdout)]
        test_logger.setLevel(logging.DEBUG)
        test_logger.propagate = True

        # Capture pre-state for our test logger (so we can restore even if it didn't exist earlier)
        pre_test_logger_state = (list(test_logger.handlers), test_logger.level, test_logger.propagate)

        try:
            # Call the function under test
            ensure_fn()

            # After calling, root must have exactly one handler that writes to stderr
            self.assertEqual(len(root.handlers), 1, "root should have exactly one handler after call")
            handler = root.handlers[0]
            self.assertIs(handler.stream, sys.stderr, "handler must write to sys.stderr")
            expected_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            self.assertIsNotNone(handler.formatter, "handler must have a formatter")
            self.assertEqual(handler.formatter._fmt, expected_fmt, "formatter must use the expected format string")

            # Root level must be CRITICAL
            self.assertEqual(root.level, logging.CRITICAL, "root level must be set to CRITICAL")

            # The test logger must have been reconfigured to use the same handler, CRITICAL level, and propagate=False
            self.assertEqual(len(test_logger.handlers), 1, "test logger should have exactly one handler")
            self.assertIs(test_logger.handlers[0], handler, "test logger must use the same stderr handler instance as root")
            self.assertEqual(test_logger.level, logging.CRITICAL, "test logger level must be CRITICAL")
            self.assertFalse(test_logger.propagate, "test logger propagation must be disabled")
        finally:
            # Restore root state
            root.handlers = orig_root_handlers
            root.setLevel(orig_root_level)

            # Restore original loggers' state
            for name, (handlers, level, propagate) in orig_logger_states.items():
                obj = logging.getLogger(name)
                obj.handlers = handlers
                obj.setLevel(level)
                obj.propagate = propagate

            # Restore test logger to its pre-test state
            test_logger.handlers = pre_test_logger_state[0]
            test_logger.setLevel(pre_test_logger_state[1])
            test_logger.propagate = pre_test_logger_state[2]
