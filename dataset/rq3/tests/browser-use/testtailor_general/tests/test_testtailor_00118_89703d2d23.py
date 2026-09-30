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
        """Verify that main constructs the browser session and runs the agent run() coroutine."""
        called = {}

        # Save originals to restore later
        orig_agent_run = getattr(Agent, "run", None)
        orig_agent_init = getattr(Agent, "__init__", None)
        orig_browser_init = getattr(BrowserSession, "__init__", None)

        try:
            # Replace Agent.run with a lightweight coroutine that records it was called
            async def _fake_run(self):
                called["agent_run"] = True

            # Replace Agent.__init__ to avoid heavy initialization
            def _fake_agent_init(self, *args, **kwargs):
                called["agent_constructed"] = True
                # Accept task and llm kwargs if provided without using them
                self._init_args = (args, kwargs)

            # Replace BrowserSession.__init__ to avoid starting a real browser.
            # Use object.__setattr__ to bypass pydantic validation/assignment issues.
            def _fake_browser_init(self, browser_profile=None, *args, **kwargs):
                called["browser_constructed"] = True
                object.__setattr__(self, "browser_profile", browser_profile)

            Agent.run = _fake_run
            Agent.__init__ = _fake_agent_init
            BrowserSession.__init__ = _fake_browser_init

            # Run the async main function without adding a top-level import statement
            __import__("asyncio").run(main())

            # Assertions: both constructions and agent.run should have been invoked
            self.assertTrue(called.get("browser_constructed", False), "BrowserSession was not constructed")
            self.assertTrue(called.get("agent_constructed", False), "Agent was not constructed")
            self.assertTrue(called.get("agent_run", False), "Agent.run was not executed")
        finally:
            # Restore originals to avoid affecting other tests
            if orig_agent_run is not None:
                Agent.run = orig_agent_run
            else:
                try:
                    delattr(Agent, "run")
                except Exception:
                    pass

            if orig_agent_init is not None:
                Agent.__init__ = orig_agent_init
            else:
                try:
                    delattr(Agent, "__init__")
                except Exception:
                    pass

            if orig_browser_init is not None:
                BrowserSession.__init__ = orig_browser_init
            else:
                try:
                    delattr(BrowserSession, "__init__")
                except Exception:
                    pass
