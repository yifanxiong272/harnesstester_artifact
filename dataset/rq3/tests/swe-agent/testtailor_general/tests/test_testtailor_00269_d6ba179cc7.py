import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.run')
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
        """Ensure the 'compare-runs' command imports and calls compare_runs.run_from_cli with remaining args."""
        import sys
        import types

        # Prepare a fake module to stand in for sweagent.run.compare_runs
        called = {}

        def fake_run_from_cli(args):
            # Record that the function was called and with what arguments
            called["args"] = args
            return 0

        fake_mod = types.ModuleType("sweagent.run.compare_runs")
        fake_mod.run_from_cli = fake_run_from_cli

        # Ensure parent packages exist in sys.modules so the import "from sweagent.run.compare_runs import ..."
        # will find our fake module.
        created = []
        if "sweagent" not in sys.modules:
            sys.modules["sweagent"] = types.ModuleType("sweagent")
            created.append("sweagent")
        if "sweagent.run" not in sys.modules:
            sys.modules["sweagent.run"] = types.ModuleType("sweagent.run")
            created.append("sweagent.run")

        # Insert our fake compare_runs module
        sys.modules["sweagent.run.compare_runs"] = fake_mod
        created.append("sweagent.run.compare_runs")

        try:
            # Import the CLI entry point and run it with the target command
            from sweagent.run.run import main

            args = ["compare-runs", "--foo", "bar"]
            main(args)

            # Verify our fake run_from_cli was called with the remaining args
            self.assertIn("args", called)
            self.assertEqual(called["args"], ["--foo", "bar"])
        finally:
            # Clean up any modules we inserted to avoid side effects on other tests
            for name in created:
                sys.modules.pop(name, None)
