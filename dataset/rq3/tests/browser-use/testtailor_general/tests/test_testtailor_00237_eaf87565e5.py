import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.browser.watchdog_base')
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
		"""Ensure duplicate handler registration raises RuntimeError in attach_handler_to_session."""

		# Create a dummy event class with the required name
		class EventName:
			pass

		# Create a watchdog-like object with a correctly named handler method
		class MyWatchdog:
			def on_EventName(self, event):
				# handler body is irrelevant for this test
				return None

		watchdog = MyWatchdog()
		handler = getattr(watchdog, 'on_EventName')

		# Prepare an existing handler that simulates a previously-registered unique handler
		existing_handler = lambda e: None
		# Set its __name__ to match the pattern unique_handler.__name__ will have:
		# f'{watchdog_class_name}.{handler.__name__}'
		existing_handler.__name__ = f'{watchdog.__class__.__name__}.{handler.__name__}'

		# Minimal fake event_bus with handlers mapping to trigger the duplicate-detection branch
		class DummyEventBus:
			def __init__(self):
				self.handlers = {EventName.__name__: [existing_handler]}

			# on(...) is not expected to be called because the duplicate check occurs earlier,
			# but provide a stub to be a well-formed object.
			def on(self, *args, **kwargs):
				raise AssertionError("on() should not be called in this test path")

		# Minimal fake browser_session that provides event_bus
		browser_session = type('BS', (), {})()
		browser_session.event_bus = DummyEventBus()

		# Call attach_handler_to_session and assert RuntimeError is raised for duplicate registration
		with self.assertRaises(RuntimeError) as cm:
			BaseWatchdog.attach_handler_to_session(browser_session, EventName, handler)

		# Sanity-check the error message contains expected details
		msg = str(cm.exception)
		self.assertIn('Duplicate handler registration attempted', msg)
		self.assertIn(EventName.__name__, msg)
		self.assertIn(f'{watchdog.__class__.__name__}.{handler.__name__}', msg)
