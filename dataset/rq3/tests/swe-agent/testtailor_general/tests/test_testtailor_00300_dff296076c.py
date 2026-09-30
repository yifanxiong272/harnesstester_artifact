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
        """Ensure the 'remove-unfinished' command imports and calls remove_unfinished.run_from_cli with remaining args."""
        # record calls
        called = {}

        def fake_run_from_cli(args):
            called["called"] = True
            called["args"] = args

        # Backup any existing modules we will override
        prev_pkg = sys.modules.get("sweagent")
        prev_run = sys.modules.get("sweagent.run")
        prev_child = sys.modules.get("sweagent.run.remove_unfinished")

        # Create simple objects to act as modules (no external imports needed)
        class Dummy:
            pass

        pkg = Dummy()
        runpkg = Dummy()
        child = Dummy()
        # attach the fake function that main will import
        child.run_from_cli = fake_run_from_cli

        # Install into sys.modules so the deferred import in main() picks them up
        sys.modules["sweagent"] = pkg
        sys.modules["sweagent.run"] = runpkg
        sys.modules["sweagent.run.remove_unfinished"] = child

        try:
            # Call the CLI entrypoint with the target command and some extra args
            main(["remove-unfinished", "one", "two"])
        finally:
            # Restore previous module state
            if prev_child is None:
                sys.modules.pop("sweagent.run.remove_unfinished", None)
            else:
                sys.modules["sweagent.run.remove_unfinished"] = prev_child

            if prev_run is None:
                sys.modules.pop("sweagent.run", None)
            else:
                sys.modules["sweagent.run"] = prev_run

            if prev_pkg is None:
                sys.modules.pop("sweagent", None)
            else:
                sys.modules["sweagent"] = prev_pkg

        # Verify our fake was called and received only the remaining arguments
        self.assertTrue(called.get("called", False), "remove_unfinished.run_from_cli was not called")
        self.assertEqual(called.get("args"), ["one", "two"])
