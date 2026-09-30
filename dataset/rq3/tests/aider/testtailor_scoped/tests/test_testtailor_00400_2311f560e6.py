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
        """Ensure step() handles extremely narrow console widths (max_spinner_width < 0)"""
        # Create a spinner instance
        spinner = Spinner("processing")

        # Force the spinner to behave as if on a TTY
        spinner.is_tty = True

        # Replace console with a mock that reports a tiny width (1) so width - 2 < 0
        mock_console = MagicMock()
        mock_console.width = 1  # Will cause console.width - 2 == -1 -> triggers branch
        mock_console.show_cursor = MagicMock()
        spinner.console = mock_console

        # Ensure frames and scan_char are set to predictable values
        spinner.frames = ["#=        "]
        spinner.scan_char = "#"
        spinner.frame_idx = 0

        # Make spinner eligible to become visible immediately
        spinner.start_time = time.time() - 1.0
        spinner.last_update = 0.0

        # Simulate a previous longer display so padding logic runs
        spinner.last_display_len = 5

        # Patch sys.stdout to capture writes and prevent actual terminal output
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.write = MagicMock()
            mock_stdout.flush = MagicMock()

            # Call step; this should hit the branch and set max_spinner_width to 0,
            # resulting in an empty line_to_display and last_display_len -> 0
            spinner.step()

            # After running, last_display_len should be updated to 0 because the
            # line was truncated to zero width
            self.assertEqual(spinner.last_display_len, 0)

            # Console cursor should have been hidden when spinner became visible
            mock_console.show_cursor.assert_called_with(False)

            # sys.stdout.write should have been used to write the clearing padding and backspaces
            self.assertTrue(mock_stdout.write.called)
            # flush should have been called once at the end
            mock_stdout.flush.assert_called_once()
