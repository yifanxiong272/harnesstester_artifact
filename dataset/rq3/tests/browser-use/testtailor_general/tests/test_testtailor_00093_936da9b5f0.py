import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.dom.markdown_extractor')
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
        """Providing both browser_session and dom_service/target_id must raise ValueError."""
        # Prepare dummy inputs - actual types aren't needed because the function
        # raises before using them (no awaits before the ValueError).
        browser_session = object()
        dom_service = object()
        target_id = "dummy-target"

        coro = extract_clean_markdown(
            browser_session=browser_session,
            dom_service=dom_service,
            target_id=target_id,
        )

        # Start the coroutine by sending None. This will execute the function
        # body up to the first await (or raise immediately). Using send(None)
        # avoids needing to import or run an event loop in the test.
        with self.assertRaisesRegex(ValueError, 'Cannot specify both browser_session and dom_service/target_id'):
            try:
                coro.send(None)
            finally:
                # Ensure the coroutine is closed to avoid ResourceWarning
                try:
                    coro.close()
                except Exception:
                    pass
