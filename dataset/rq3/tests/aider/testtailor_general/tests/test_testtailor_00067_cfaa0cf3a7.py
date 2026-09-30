import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.run_cmd')
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
        """Ensure run_cmd handles OSError and formats/forwards the error message."""
        import importlib
        import io
        import sys
        from unittest import mock

        # Locate the module that defines run_cmd
        candidates = ["aider.utils", "aider.commands", "aider.io", "aider", "__main__"]
        target_mod = None
        for name in candidates:
            try:
                mod = importlib.import_module(name)
            except Exception:
                continue
            if hasattr(mod, "run_cmd"):
                target_mod = mod
                break

        if target_mod is None:
            self.fail("Could not locate module containing run_cmd")

        # Case 1: error_print provided -> should call the provided callable with the message
        mock_error_print = mock.MagicMock()
        with mock.patch.object(sys.stdin, "isatty", side_effect=OSError("nope")):
            rc, msg = target_mod.run_cmd("my-test-cmd", verbose=False, error_print=mock_error_print, cwd=None)

        self.assertEqual(rc, 1)
        expected_prefix = "Error occurred while running command 'my-test-cmd':"
        self.assertTrue(msg.startswith(expected_prefix))
        self.assertIn("nope", msg)
        mock_error_print.assert_called_once_with(msg)

        # Case 2: error_print is None -> should print the message to stdout
        with mock.patch.object(sys.stdin, "isatty", side_effect=OSError("boom")):
            stdout = io.StringIO()
            with mock.patch("sys.stdout", new=stdout):
                rc2, msg2 = target_mod.run_cmd("another-cmd", verbose=False, error_print=None, cwd=None)

        self.assertEqual(rc2, 1)
        self.assertIn("boom", msg2)
        printed = stdout.getvalue()
        self.assertIn(msg2, printed)
