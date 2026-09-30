import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.browser.utils')
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
        """complete the test case here"""
        # Create a minimal observation object with attributes accessed by get_agent_obs_text
        class DummyObs:
            pass

        obs = DummyObs()
        obs.trigger_by_action = ActionType.BROWSE_INTERACTIVE
        obs.url = "http://example.com"
        obs.focused_element_bid = "bid-001"
        obs.screenshot_path = "/tmp/screenshot.png"
        obs.error = True
        obs.last_browser_action_error = "Simulated error: click failed"
        # Provide values for attributes used by get_axtree_str; content not used in this branch
        obs.axtree_object = {"root": {}}
        obs.extra_element_properties = {}
        obs.filter_visible_only = False
        obs.content = ""

        # Patch get_axtree_str in the function's globals to return a predictable string
        original_get_axtree_str = get_agent_obs_text.__globals__.get("get_axtree_str")
        get_agent_obs_text.__globals__["get_axtree_str"] = (
            lambda axtree_object, extra_element_properties, filter_visible_only=False: "FAKE_AXTREE"
        )

        try:
            result = get_agent_obs_text(obs)
        finally:
            # Restore original function to avoid side effects on other tests
            if original_get_axtree_str is None:
                del get_agent_obs_text.__globals__["get_axtree_str"]
            else:
                get_agent_obs_text.__globals__["get_axtree_str"] = original_get_axtree_str

        # Verify that the error message block (the target code) is included in the output
        self.assertIn("[Current URL: http://example.com]", result)
        self.assertIn("[Screenshot saved to: /tmp/screenshot.png]", result)
        self.assertIn("================ BEGIN error message ===============", result)
        self.assertIn("The following error occurred when executing the last action:", result)
        self.assertIn("Simulated error: click failed", result)
        self.assertIn("================ END error message ===============", result)
        # Also assert accessibility tree placeholder was used
        self.assertIn("============== BEGIN accessibility tree ==============", result)
        self.assertIn("FAKE_AXTREE", result)
