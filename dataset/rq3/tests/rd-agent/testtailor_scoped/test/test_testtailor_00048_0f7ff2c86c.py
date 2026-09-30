import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.data_science.proposal.exp_gen.trace_scheduler')
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
        """Awaiting the abstract TraceScheduler.next coroutine should raise NotImplementedError."""
        # Calling the async method returns a coroutine; the NotImplementedError is raised when awaited.
        coro = TraceScheduler.next(None, None)
        loop = asyncio.new_event_loop()
        try:
            with self.assertRaises(NotImplementedError):
                loop.run_until_complete(coro)
        finally:
            loop.close()
