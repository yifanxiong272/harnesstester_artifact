import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.api.utils')
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
        """Ensure _get_my_tid returns the cached _thread_id when thread is alive."""
        ev = threading.Event()

        def worker():
            # block until test signals completion
            ev.wait()

        t = ThreadWithExc(target=worker)
        t.start()

        # wait (briefly) for the thread to become alive
        for _ in range(1000):
            if t.is_alive():
                break

        self.assertTrue(t.is_alive(), "Thread failed to start and become alive")

        # set the cached id and ensure the method returns it
        sentinel_tid = 99999
        t._thread_id = sentinel_tid
        returned = t._get_my_tid()
        self.assertEqual(returned, sentinel_tid)
        self.assertEqual(t._thread_id, sentinel_tid)

        # cleanup: unblock and join the thread
        ev.set()
        t.join(timeout=1)
        self.assertFalse(t.is_alive())
