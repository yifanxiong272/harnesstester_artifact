import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.copypaste')
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
        """Call main() so it invokes watcher.start() and ensure watcher.stop() is called via the KeyboardInterrupt path."""
        # Save originals
        orig_start = ClipboardWatcher.start
        orig_stop = ClipboardWatcher.stop
        orig_init = ClipboardWatcher.__init__

        created = {}

        # Wrap __init__ to capture the watcher instance created in main
        def fake_init(self, io, verbose=False):
            orig_init(self, io, verbose)
            created['watcher'] = self

        # Make start raise KeyboardInterrupt to trigger the except branch in main
        def fake_start(self):
            raise KeyboardInterrupt

        # Make stop record that it was called
        def fake_stop(self):
            setattr(self, "stop_called", True)

        try:
            ClipboardWatcher.__init__ = fake_init
            ClipboardWatcher.start = fake_start
            ClipboardWatcher.stop = fake_stop

            # Call main() which should call our fake_start (raising KeyboardInterrupt)
            # and then call fake_stop on the watcher instance.
            main()

            # Verify watcher was created and stop was called
            self.assertIn('watcher', created)
            self.assertTrue(getattr(created['watcher'], "stop_called", False))
        finally:
            # Restore originals
            ClipboardWatcher.start = orig_start
            ClipboardWatcher.stop = orig_stop
            ClipboardWatcher.__init__ = orig_init
