import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.cli')
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
        """Verify the top-level ArgumentParser (parser) is configured as expected."""
        import importlib
        import argparse

        # Try common module names that might expose the top-level 'parser'
        module_candidates = ['pr_agent.cli', 'cli', 'pr_agent.__main__']
        mod = None
        for name in module_candidates:
            try:
                mod = importlib.import_module(name)
                break
            except Exception:
                continue
        self.assertIsNotNone(mod, f"Could not import any of the candidate modules: {module_candidates}")

        # Get parser from module, or build it if only a factory is exposed
        parser = getattr(mod, 'parser', None)
        if parser is None and hasattr(mod, 'set_parser'):
            parser = mod.set_parser()
        self.assertIsNotNone(parser, "Expected a 'parser' object to be present on the module")

        # Basic parser metadata
        self.assertEqual(parser.description, 'AI based pull request analyzer')

        # Helper to find actions
        def find_action_by_option(opt):
            for a in parser._actions:
                if hasattr(a, 'option_strings') and opt in a.option_strings:
                    return a
            return None

        def find_action_by_dest(dest):
            for a in parser._actions:
                if getattr(a, 'dest', None) == dest:
                    return a
            return None

        # --pr_url argument
        pr_action = find_action_by_option('--pr_url')
        self.assertIsNotNone(pr_action, "Expected '--pr_url' argument to be present")
        self.assertEqual(pr_action.default, None)
        self.assertIn('PR', (pr_action.help or '').upper())

        # --issue_url argument
        issue_action = find_action_by_option('--issue_url')
        self.assertIsNotNone(issue_action, "Expected '--issue_url' argument to be present")
        self.assertEqual(issue_action.default, None)

        # --version action
        version_action = find_action_by_option('--version')
        self.assertIsNotNone(version_action, "Expected '--version' argument to be present")
        ver_str = getattr(version_action, 'version', None)
        self.assertIsNotNone(ver_str)
        self.assertTrue(ver_str.startswith('pr-agent '), f"version string not as expected: {ver_str}")

        # positional 'command'
        cmd_action = find_action_by_dest('command')
        self.assertIsNotNone(cmd_action, "Expected positional 'command' to be present")
        self.assertIsNotNone(getattr(cmd_action, 'choices', None))
        self.assertIn('review', cmd_action.choices)

        # positional 'rest' should be configured to capture the remainder
        rest_action = find_action_by_dest('rest')
        self.assertIsNotNone(rest_action, "Expected positional 'rest' to be present")
        self.assertEqual(rest_action.nargs, argparse.REMAINDER)
