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
        """Raise ValueError when both browser_session and dom_service/target_id are provided."""
        # Provide a non-None browser_session and a non-None dom_service to trigger the validation error.
        browser_session = object()
        dom_service = object()

        coro = extract_clean_markdown(browser_session=browser_session, dom_service=dom_service)
        with self.assertRaises(ValueError) as cm:
            try:
                # Start the coroutine execution synchronously up to the first await.
                # The parameter validation runs immediately and should raise ValueError.
                coro.send(None)
            finally:
                # Ensure the coroutine is properly closed to avoid warnings.
                try:
                    coro.close()
                except Exception:
                    pass

        self.assertIn('Cannot specify both browser_session and dom_service/target_id', str(cm.exception))
