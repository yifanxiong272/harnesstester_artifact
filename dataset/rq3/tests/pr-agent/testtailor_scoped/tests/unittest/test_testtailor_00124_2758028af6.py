import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.mosaico.dispatch')
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
        """When an unexpected exception occurs inside route_and_run, it must return the
        standard internal-error fallback string rather than propagating."""
        # Patch an internal helper (resolved from the function's actual module) to raise
        # so route_and_run's top-level except is exercised.
        mod_path = route_and_run.__module__
        with patch(f"{mod_path}._find_pr_url", side_effect=Exception("boom")):
            ai = __import__("asyncio")
            loop = ai.new_event_loop()
            try:
                res = loop.run_until_complete(route_and_run("trigger error"))
            finally:
                loop.close()
        expected = "PR-Agent could not complete the request (internal error; see agent logs)."
        self.assertEqual(res, expected)
