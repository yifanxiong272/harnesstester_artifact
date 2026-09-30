import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.core.loop')
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
        """runtime already has a status_callback -> run_agent_until_done should raise"""
        # Minimal stubs to satisfy the function signature. The function raises
        # before inspecting controller or memory, so these can be simple.
        class DummyRuntime:
            def __init__(self):
                # non-None/truthy status_callback triggers the ValueError branch
                self.status_callback = lambda msg_type, runtime_status, msg: None

        class DummyState:
            agent_state = 'RUNNING'

        class DummyController:
            def __init__(self):
                self.state = DummyState()
                self.status_callback = None
                self.state = DummyState()

        class DummyMemory:
            def __init__(self):
                self.status_callback = None

        runtime = DummyRuntime()
        controller = DummyController()
        memory = DummyMemory()
        end_states = ['DONE']

        # run_agent_until_done is async; run it in a fresh event loop and assert it raises
        with self.assertRaises(ValueError) as cm:
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    run_agent_until_done(controller, runtime, memory, end_states)
                )
            finally:
                loop.close()
                # restore no event loop for cleanliness
                try:
                    asyncio.set_event_loop(None)
                except Exception:
                    pass

        self.assertIn('Runtime status_callback was set', str(cm.exception))
