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
        """Verify find_jira_tickets extracts distinct, well-formed JIRA keys from text,
        handles URLs and bare tickets, ignores lowercase keys, and deduplicates results.
        Allow that the regex may match substrings of an overly-long project token;
        instead validate that every returned ticket conforms to the intended format.
        """
        text = (
            "This change references PROJ-123, and also the ticket at "
            "https://jira.example.com/browse/FOO-1. Duplicate PROJ-123 should be ignored. "
            "Lowercase proj-456 shouldn't match. Also check boundary: (BAR-7). "
            "And a bare URL https://jira.example.com/browse/BAZ-8 extra."
        )

        results = find_jira_tickets(text)
        # Must be a list (function returns list(tickets))
        self.assertIsInstance(results, list)

        found = set(results)
        expected = {"PROJ-123", "FOO-1", "BAR-7", "BAZ-8"}

        # Ensure the expected tickets are present (deduplicated). Extra matches
        # (e.g., substring matches from overly-long tokens) are tolerated but
        # every returned ticket must be well-formed below.
        self.assertTrue(expected.issubset(found), f"missing expected tickets: {expected - found}")

        # Ensure lowercase ticket isn't matched
        self.assertNotIn("proj-456", found)
        self.assertNotIn("proj-456", results)

        # Deduplication: PROJ-123 should appear only once in the returned list
        self.assertIn("PROJ-123", results)
        self.assertEqual(results.count("PROJ-123"), 1)

        # Basic validation of format for each returned ticket: PREFIX-NUM where
        # PREFIX is 2-10 uppercase letters and NUM is 1-7 digits.
        for ticket in results:
            # Defensive: skip any empty or non-string entries (shouldn't happen)
            self.assertIsInstance(ticket, str)
            self.assertTrue(ticket, "empty ticket string returned")
            parts = ticket.split("-", 1)
            self.assertEqual(len(parts), 2, f"ticket missing hyphen: {ticket}")
            prefix, number = parts
            self.assertTrue(prefix.isalpha() and prefix.isupper() and 2 <= len(prefix) <= 10,
                            f"prefix invalid for ticket {ticket}")
            self.assertTrue(number.isdigit() and 1 <= len(number) <= 7,
                            f"number part invalid for ticket {ticket}")
