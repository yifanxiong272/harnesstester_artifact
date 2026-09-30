import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.run_single')
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
        """Verify RunSingleConfig._get_auto_correct returns the expected ACS entries."""
        acs_list = RunSingleConfig._get_auto_correct()

        # Basic structure checks
        self.assertIsInstance(acs_list, list)
        self.assertEqual(len(acs_list), 9)

        # Build a lookup by original name
        lookup = {item.original: item for item in acs_list}

        # Entries that should have alternatives
        expected_alts = {
            "model": "agent.model.name",
            "agent.model": "agent.model.name",
            "model.name": "agent.model.name",
            "per_instance_cost_limit": "agent.model.per_instance_cost_limit",
            "model.per_instance_cost_limit": "agent.model.per_instance_cost_limit",
            "config_file": "config",
            "repo.path": "env.repo.path",
        }
        for orig, alt in expected_alts.items():
            self.assertIn(orig, lookup, msg=f"{orig} not present in auto-correct list")
            item = lookup[orig]
            # alternative should match exactly
            self.assertEqual(item.alternative, alt)
            # Items with alternatives should not have a help string (allow None or empty)
            self.assertFalse(item.help)
            # format() should mention both the original and the alternative (color tags may be present)
            formatted = item.format()
            self.assertIn(f"--{orig}", formatted)
            self.assertIn(f"--{alt}", formatted)

        # Entries that should have help (and no alternative)
        for help_key, expected_snippet in [
            ("data_path", "no longer support for SWE-A 1.0"),
            ("repo_path", "no longer support for SWE-A 1.0"),
        ]:
            self.assertIn(help_key, lookup, msg=f"{help_key} not present in auto-correct list")
            item = lookup[help_key]
            # Should have empty alternative string (constructor uses "" as default)
            self.assertEqual(item.alternative, "")
            # Should have help text and it should contain the expected snippet
            self.assertIsNotNone(item.help)
            self.assertIn(expected_snippet, item.help)
            # format() should return the help text verbatim
            self.assertEqual(item.format(), item.help)

        # show() behavior: works with plain flag and with equals-form (--flag=value)
        self.assertTrue(lookup["model"].show([f"--model"]))
        self.assertTrue(lookup["model"].show([f"--model=somevalue"]))
        self.assertTrue(lookup["data_path"].show([f"--data_path"]))
        self.assertTrue(lookup["repo_path"].show([f"--repo_path=xyz"]))
