import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.actor.playground.flights')
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
        """Run the async main coroutine from the target module using mocks, avoiding CLI parsing side-effects."""
        import sys, inspect, asyncio, builtins

        # Try to find an already-loaded module that defines an async main to avoid importing modules that run CLI parsing on import.
        module = None
        for m in list(sys.modules.values()):
            try:
                if m and hasattr(m, 'main') and inspect.iscoroutinefunction(getattr(m, 'main')):
                    module = m
                    break
            except Exception:
                continue

        # If none found in sys.modules, try a few common module names but ignore import-time errors.
        if module is None:
            for name in ('solution', 'main', 'app', 'user_code', 'program'):
                try:
                    m = __import__(name)
                except Exception:
                    continue
                try:
                    if hasattr(m, 'main') and inspect.iscoroutinefunction(getattr(m, 'main')):
                        module = m
                        break
                except Exception:
                    continue

        if module is None or not hasattr(module, 'main') or not inspect.iscoroutinefunction(module.main):
            raise ImportError("Could not find the target module with an async 'main' coroutine")

        # Mocks
        class MockElement:
            instances = []

            def __init__(self, prompt):
                self.prompt = prompt
                self.clicked = False
                MockElement.instances.append(self)

            async def click(self):
                self.clicked = True

        class MockPage:
            def __init__(self):
                self.url = None

            async def goto(self, url):
                self.url = url

            async def must_get_element_by_prompt(self, prompt, llm):
                return MockElement(prompt)

        class MockBrowser:
            def __init__(self, keep_alive=True):
                self.keep_alive = keep_alive
                self.started = False

            async def start(self):
                self.started = True

            async def stop(self):
                self.started = False

            async def get_current_page(self):
                return None

            async def new_page(self):
                return MockPage()

        class MockAgent:
            last_instance = None

            def __init__(self, task, llm, browser_session):
                self.task = task
                self.llm = llm
                self.browser_session = browser_session
                self.ran = False
                MockAgent.last_instance = self

            async def run(self):
                self.ran = True

        class MockLLM:
            pass

        # Patch module globals
        module.Browser = MockBrowser
        module.Agent = MockAgent
        module.llm = MockLLM()

        # Fast sleep to avoid delays
        async def _fast_sleep(_=None):
            return None

        orig_module_asyncio_sleep = None
        if hasattr(module, 'asyncio'):
            try:
                orig_module_asyncio_sleep = module.asyncio.sleep
                module.asyncio.sleep = _fast_sleep
            except Exception:
                orig_module_asyncio_sleep = None

        orig_asyncio_sleep = asyncio.sleep
        asyncio.sleep = _fast_sleep

        # Patch input so it does not block
        orig_input = builtins.input
        builtins.input = lambda prompt='': ''

        try:
            asyncio.run(module.main())
        finally:
            # Restore patched globals
            builtins.input = orig_input
            asyncio.sleep = orig_asyncio_sleep
            if orig_module_asyncio_sleep is not None:
                module.asyncio.sleep = orig_module_asyncio_sleep

        # Assertions
        self.assertIsNotNone(MockAgent.last_instance, "Agent was not instantiated")
        self.assertTrue(MockAgent.last_instance.ran, "Agent.run() was not executed")

        self.assertGreaterEqual(len(MockElement.instances), 2, "Expected at least two prompt-based elements")
        self.assertTrue(MockElement.instances[-1].clicked, "The most recent element was not clicked")
        self.assertTrue(MockElement.instances[-2].clicked, "The second most recent element was not clicked")
