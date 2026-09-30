import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.dom.playground.multi_act')
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
        """Test that main creates a BrowserSession with the expected viewport and runs Agent.run()"""
        # Access the globals of the module where main is defined so we can monkeypatch the names used there.
        mod_globals = main.__globals__

        orig_BrowserSession = mod_globals.get('BrowserSession')
        orig_Agent = mod_globals.get('Agent')

        try:
            # Dummy replacements to avoid external side effects (real browser/LLM usage).
            class DummyBrowserSession:
                last_instance = None

                def __init__(self, browser_profile=None):
                    DummyBrowserSession.last_instance = self
                    self.browser_profile = browser_profile

            class DummyAgent:
                last_instance = None

                def __init__(self, task=None, llm=None):
                    DummyAgent.last_instance = self
                    self.task = task
                    self.llm = llm
                    self.run_called = False

                async def run(self):
                    # Simulate some async work
                    self.run_called = True
                    return None

            # Inject dummies into the module where main() will look them up
            mod_globals['BrowserSession'] = DummyBrowserSession
            mod_globals['Agent'] = DummyAgent

            # Get asyncio without using an import statement (use the built-in importer).
            bi = mod_globals.get('__builtins__')
            if isinstance(bi, dict):
                importer = bi.get('__import__')
            else:
                importer = getattr(bi, '__import__')
            asyncio = importer('asyncio')

            # Run the async main() function safely whether or not an event loop is already running.
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = None

            if loop is None or loop.is_running():
                # Create a fresh loop for the test to avoid interfering with any running loop.
                new_loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(new_loop)
                    new_loop.run_until_complete(main())
                finally:
                    new_loop.close()
                    # Try to restore the previous event loop (best-effort).
                    try:
                        asyncio.set_event_loop(loop)
                    except Exception:
                        pass
            else:
                loop.run_until_complete(main())

            # Assertions:
            # - A BrowserSession instance was created and had a browser_profile with expected viewport width.
            self.assertIsNotNone(DummyBrowserSession.last_instance, "BrowserSession was not instantiated")
            bp = DummyBrowserSession.last_instance.browser_profile
            self.assertIsNotNone(bp, "BrowserProfile was not passed to BrowserSession")

            # Try to read the viewport width in a couple of safe ways.
            width = None
            try:
                # If window_size supports __getitem__ (ViewportSize from project), this will work.
                width = bp.window_size['width']
            except Exception:
                # Fallback: attribute access
                try:
                    width = getattr(bp.window_size, 'width', None)
                except Exception:
                    width = None

            self.assertEqual(width, 1100, "Viewport width was not set to 1100")

            # - An Agent instance was created and its run() was awaited.
            self.assertIsNotNone(DummyAgent.last_instance, "Agent was not instantiated")
            self.assertTrue(DummyAgent.last_instance.run_called, "Agent.run() was not called")

            # - The Agent received the expected task string from the module globals.
            expected_task = mod_globals.get('TASK')
            if expected_task is not None:
                self.assertEqual(DummyAgent.last_instance.task, expected_task)
        finally:
            # Restore original objects to avoid side effects for other tests.
            if orig_BrowserSession is not None:
                mod_globals['BrowserSession'] = orig_BrowserSession
            else:
                mod_globals.pop('BrowserSession', None)

            if orig_Agent is not None:
                mod_globals['Agent'] = orig_Agent
            else:
                mod_globals.pop('Agent', None)
