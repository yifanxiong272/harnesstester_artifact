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
        # Ensure the branch `if args is None` is taken by calling with None and
        # setting sys.argv so BasicCLI will hit the --help branch and exit(0).
        old_argv = sys.argv[:]
        try:
            sys.argv = ["sweagent", "--help"]
            with self.assertRaises(SystemExit) as cm:
                run_from_cli(None)
            # BasicCLI prints help and calls exit(0)
            self.assertEqual(cm.exception.code, 0)
        finally:
            sys.argv = old_argv
