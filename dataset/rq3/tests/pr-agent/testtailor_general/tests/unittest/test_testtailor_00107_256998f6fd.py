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
        """Verify run_command builds args correctly and calls run with parsed args."""
        pr_url = "https://example.com/repo/pull/1"
        command = "/review"

        # Replace the real 'run' used by run_command with a fake to capture the passed args
        orig_run = run_command.__globals__['run']
        captured = {}

        def fake_run(*, args=None, inargs=None):
            captured['args'] = args
            return None

        run_command.__globals__['run'] = fake_run
        try:
            # Call the function under test
            run_command(pr_url, command)

            # Ensure our fake was called and received an argparse.Namespace
            self.assertIn('args', captured)
            args = captured['args']
            self.assertIsNotNone(args)
            # Check that the parser parsed the pr_url and the command (without leading '/')
            self.assertEqual(args.pr_url, pr_url)
            self.assertEqual(args.command, "review")
            # 'rest' should be an empty list by default
            self.assertEqual(args.rest, [])
        finally:
            # Restore original run to avoid side effects on other tests
            run_command.__globals__['run'] = orig_run
