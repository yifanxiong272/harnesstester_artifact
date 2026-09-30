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
        """KeyboardInterrupt in main should print stop message and call watcher.stop()"""
        # simple Dummy InputOutput that accepts attribute assignment
        class DummyIO:
            pass

        # track whether stop was called
        stop_called = {"called": False}

        def fake_stop(self):
            stop_called["called"] = True

        # simple stdout replacement to capture prints without importing io
        class DummyStdout:
            def __init__(self):
                self._buf = []
            def write(self, s):
                # sys.stdout.write may be called with non-string occasionally; ensure str
                self._buf.append(str(s))
            def flush(self):
                pass
            def getvalue(self):
                return "".join(self._buf)

        with unittest.mock.patch("aider.io.InputOutput", new=DummyIO):
            with unittest.mock.patch.object(ClipboardWatcher, "start", new=lambda self: None):
                with unittest.mock.patch.object(ClipboardWatcher, "stop", new=fake_stop):
                    with unittest.mock.patch("time.sleep", side_effect=KeyboardInterrupt):
                        buf = DummyStdout()
                        with unittest.mock.patch("sys.stdout", new=buf):
                            main()
                        output = buf.getvalue()

        self.assertIn("Stopped watching clipboard", output)
        self.assertTrue(stop_called["called"])
