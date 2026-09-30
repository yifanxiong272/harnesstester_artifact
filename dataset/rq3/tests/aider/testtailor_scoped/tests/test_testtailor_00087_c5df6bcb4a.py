import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.waiting')
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
        """Ensure main() completes the loop and prints Success! quickly."""
        mod_globals = main.__globals__

        # Save originals to restore later
        orig_spinner = mod_globals.get("Spinner")
        orig_sleep = mod_globals.get("time").sleep

        class FakeSpinner:
            def __init__(self, text):
                self.text = text
                self.steps = 0
                self.ended = False

            def step(self, text: str = None):
                if text is not None:
                    self.text = text
                self.steps += 1

            def end(self):
                self.ended = True

        try:
            # Patch Spinner and time.sleep to make the loop fast and non-stdout-writing
            mod_globals["Spinner"] = FakeSpinner
            mod_globals["time"].sleep = lambda s: None

            # Patch built-in print to observe the "Success!" call
            with unittest.mock.patch("builtins.print") as mock_print:
                main()
                mock_print.assert_any_call("Success!")
        finally:
            # Restore originals
            mod_globals["Spinner"] = orig_spinner
            mod_globals["time"].sleep = orig_sleep
