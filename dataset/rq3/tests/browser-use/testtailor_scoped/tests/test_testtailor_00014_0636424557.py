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
		"""When no stderr handler exists on the root logger, a new StreamHandler(sys.stderr)
		is created, applied to root.handlers, and assigned to all existing loggers with
		level CRITICAL and propagate False. Also the handler must have the expected formatter.
		"""
		# Import the module under test here to avoid top-level import statements
		from browser_use.mcp import server as server_module
		import logging
		import sys

		# Prepare: capture original root state to restore later
		orig_root_handlers = list(logging.root.handlers)
		orig_root_level = logging.root.level

		# Create a test logger that will appear in logging.root.manager.loggerDict
		test_logger_name = 'test.ensure_stderr_logger'
		test_logger = logging.getLogger(test_logger_name)

		# Capture original state for all currently-registered loggers (including our test logger)
		logger_names = list(logging.root.manager.loggerDict.keys())
		orig_logger_states: dict[str, tuple[list[logging.Handler], int, bool]] = {}
		for name in logger_names:
			lobj = logging.getLogger(name)
			orig_logger_states[name] = (list(lobj.handlers), lobj.level, lobj.propagate)

		# Ensure root has no handlers so the function will create a new stderr handler
		logging.root.handlers = []

		# Give the test logger a non-stderr handler and non-CRITICAL level so we can detect the change
		stdout_handler = logging.StreamHandler(sys.stdout)
		test_logger.handlers = [stdout_handler]
		test_logger.setLevel(logging.DEBUG)
		test_logger.propagate = True

		try:
			# Call the function under test — should create a new stderr handler and apply it
			server_module._ensure_all_loggers_use_stderr()

			# Root logger checks
			self.assertEqual(len(logging.root.handlers), 1, "root should have exactly one handler after call")
			root_handler = logging.root.handlers[0]
			self.assertIsInstance(root_handler, logging.StreamHandler)
			self.assertIs(root_handler.stream, sys.stderr, "root handler must stream to sys.stderr")
			self.assertEqual(logging.root.level, logging.CRITICAL, "root level must be set to CRITICAL")

			# Formatter check (must match the one set in the function)
			expected_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
			self.assertIsNotNone(root_handler.formatter, "handler must have a formatter")
			self.assertEqual(root_handler.formatter._fmt, expected_fmt)

			# Test logger should have been updated to use the same stderr handler
			updated_logger = logging.getLogger(test_logger_name)
			self.assertEqual(len(updated_logger.handlers), 1, "existing logger should have exactly one handler after call")
			self.assertIs(updated_logger.handlers[0], root_handler, "logger handler must be the same stderr handler used by root")
			self.assertEqual(updated_logger.level, logging.CRITICAL, "logger level must be set to CRITICAL")
			self.assertFalse(updated_logger.propagate, "logger.propagate must be False to prevent duplicate output")

		finally:
			# Restore original root state to avoid test pollution
			logging.root.handlers = orig_root_handlers
			logging.root.setLevel(orig_root_level)

			# Restore original logger states for all captured loggers
			for name, (handlers, lvl, prop) in orig_logger_states.items():
				lobj = logging.getLogger(name)
				lobj.handlers = handlers
				lobj.setLevel(lvl)
				lobj.propagate = prop
