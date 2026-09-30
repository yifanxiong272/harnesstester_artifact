import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.tools.ticket_pr_compliance_check')
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
        """Exercise the branch where re.findall returns a tuple so the
        tuple-handling logic (next(... reversed(match) ...)) is executed."""
        # Grab the target function (available in the test runtime globals)
        find_fn = globals().get("find_jira_tickets")
        self.assertIsNotNone(find_fn, "find_jira_tickets is not available in globals()")

        # Replace re.findall temporarily so that the second pattern returns a tuple.
        re_mod = __import__("re")
        original_findall = re_mod.findall

        def fake_findall(pattern, text):
            # For the first pattern (no groups) return a normal string match
            if pattern.startswith(r"\b"):
                return ["PROJ-1"]
            # For the second pattern, return a tuple to trigger the tuple branch
            return [("http://example.com/browse/PROJ-42", "PROJ-42")]

        re_mod.findall = fake_findall
        try:
            tickets = find_fn("any text")
            # The tuple-branch should extract "PROJ-42"
            self.assertIn("PROJ-42", tickets)
            # Also ensure the normal-match from the first pattern was collected
            self.assertIn("PROJ-1", tickets)
        finally:
            # Restore original implementation
            re_mod.findall = original_findall
