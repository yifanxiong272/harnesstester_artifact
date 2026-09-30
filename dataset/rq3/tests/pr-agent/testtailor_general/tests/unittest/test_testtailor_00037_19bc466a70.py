import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.servers.gerrit_server')
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
        """Ensure handle_gerrit_request sets context settings and calls PRAgent.handle_request with proper args."""
        item = Item(refspec="refs/heads/main", project="example_proj", msg="  Hello Gerrit  ")

        calls = []

        async def fake_handle_request(self, pr_url, request, notify=None):
            calls.append((pr_url, request, notify))
            return True

        # Ensure we can patch the module-level `context` used by handle_gerrit_request
        mod_name = handle_gerrit_request.__module__
        sys = __import__('sys')
        module = sys.modules[mod_name]

        # Save original context to restore later
        had_original_context = hasattr(module, "context")
        original_context = getattr(module, "context", None)

        try:
            # Replace context with a plain dict so assignment inside the handler won't raise
            setattr(module, "context", {})

            # Patch PRAgent.handle_request to avoid running the full agent logic
            with unittest.mock.patch.object(PRAgent, "handle_request", new=fake_handle_request):
                # Run the async handler
                __import__('asyncio').run(handle_gerrit_request(Action.review, item))

            # Assert that our fake handle_request was called once with expected values
            self.assertEqual(len(calls), 1)
            expected_pr_url = f"{item.project}:{item.refspec}"
            expected_request = f"/{item.msg.strip()}"
            self.assertEqual(calls[0][0], expected_pr_url)
            self.assertEqual(calls[0][1], expected_request)

            # Assert that context["settings"] was set and is a deep copy (not the same object as module.global_settings)
            self.assertIn("settings", module.context)
            self.assertIsNot(module.context["settings"], getattr(module, "global_settings"))
        finally:
            # Restore original context to avoid side effects on other tests
            if had_original_context:
                setattr(module, "context", original_context)
            else:
                if hasattr(module, "context"):
                    delattr(module, "context")
