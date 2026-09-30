import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.utils.log_streamer')
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
        """Ensure that when the stop event is set by the generator during iteration
        the loop hits the 'break' and no debug log is emitted for the yielded line.
        This calls _stream_logs directly (no thread) to avoid racing issues.
        """
        mock_log_fn = Mock()

        # Create a minimal generator that sets the streamer's stop event when iterated,
        # then yields one line. This should cause the loop to break before logging.
        class OneShotGenerator:
            def __init__(self):
                self._yielded = False
                self.closed = False
                self.streamer = None

            def __iter__(self):
                return self

            def __next__(self):
                if self._yielded or self.closed:
                    raise StopIteration
                # set the streamer's stop event so the loop will break after this yield
                if self.streamer is not None:
                    self.streamer._stop_event.set()
                self._yielded = True
                return b'should be ignored\n'

            def close(self):
                self.closed = True

        gen = OneShotGenerator()

        # Instantiate LogStreamer without running its __init__ to avoid starting threads.
        streamer = object.__new__(LogStreamer)
        # Initialize the attributes that _stream_logs expects
        streamer.log = mock_log_fn
        streamer.stdout_thread = None
        streamer.log_generator = gen
        streamer._stop_event = threading.Event()

        # Give the generator a reference to the streamer so it can set the stop event.
        gen.streamer = streamer

        # Call the method under test directly.
        streamer._stream_logs()

        # Verify that no debug-level log was emitted for the yielded line (loop should break)
        called_levels = [call_args[0][0] for call_args in mock_log_fn.call_args_list]
        self.assertFalse(any(level == 'debug' for level in called_levels), "No debug logs should have been emitted")

        # Ensure the generator still exists and did yield once
        self.assertTrue(gen._yielded, "Generator should have yielded once")
