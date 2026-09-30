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
        """Ensure ThreadWithExc._get_my_tid finds and caches the thread id from threading._active."""
        evt = threading.Event()

        def target():
            # block until the test lets the thread finish
            evt.wait()

        t = ThreadWithExc(target=target)
        t.start()

        # ensure thread has started and is present in threading._active
        for _ in range(100):
            if t.is_alive():
                break
            threading.Event().wait(0.001)
        self.assertTrue(t.is_alive(), "thread failed to start")

        # call _get_my_tid from the test (caller) thread; it should find the thread in threading._active,
        # set the _thread_id attribute and return the tid
        tid = t._get_my_tid()
        self.assertTrue(hasattr(t, "_thread_id"))
        self.assertEqual(t._thread_id, tid)
        # verify threading._active maps that tid back to our thread object
        self.assertIs(threading._active[tid], t)

        # cleanup: allow thread to exit and join
        evt.set()
        t.join(timeout=1)
        self.assertFalse(t.is_alive())
