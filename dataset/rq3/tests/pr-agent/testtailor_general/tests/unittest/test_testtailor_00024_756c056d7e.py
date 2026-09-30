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
        """Exercise find_jira_tickets with plain tickets, URLs, duplicates and boundary cases."""
        # Construct a text containing:
        # - a plain ticket repeated twice (duplicate)
        # - a ticket inside a JIRA browse URL
        # - another plain ticket
        # - an all-uppercase 10-char project key (allowed)
        # - a ticket with the max allowed 7-digit number
        # - some invalid forms that must NOT be matched (lowercase key, mixed-case too-long key, too many digits)
        text = (
            "Please address PROJ-123 and again PROJ-123. See details at "
            "https://jira.example.com/browse/PROJ-456. Also: OTHERPROJ-7. "
            "ALLOWEDKEY-98765 BIG-1234567. Do not match proj-9 or Toolongkeyx-1 or TOOBIG-12345678."
        )

        # Call the function under test (assumed to be available in the test namespace).
        tickets = find_jira_tickets(text)

        # Verify results: set equality (order is not guaranteed), uniqueness, and correct membership
        expected = {"PROJ-123", "PROJ-456", "OTHERPROJ-7", "ALLOWEDKEY-98765", "BIG-1234567"}
        self.assertSetEqual(set(tickets), expected)
        self.assertEqual(len(tickets), len(set(tickets)))  # ensure no duplicates returned

        # Ensure invalid forms were not included
        self.assertNotIn("proj-9", tickets)
        self.assertNotIn("Toolongkeyx-1", tickets)
        self.assertNotIn("TOOBIG-12345678", tickets)

        # Ensure all returned items are strings and match the general expected pattern
        for t in tickets:
            self.assertIsInstance(t, str)
            self.assertRegex(t, r'^[A-Z]{2,10}-\d{1,7}$')
