import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.diffs')
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
        """Calling main() with the wrong number of argv entries prints usage and exits 1."""
        old_argv = sys.argv[:]
        try:
            # make argv length != 3 to hit the target branch
            sys.argv[:] = ["diffs.py"]  # length 1

            captured = []

            class DummyStdout:
                def write(self, s):
                    # sys.stdout.write may be passed non-string (e.g., bytes) in some contexts;
                    # ensure we only collect strings.
                    try:
                        captured.append(str(s))
                    except Exception:
                        captured.append("")
                def flush(self):
                    pass

            old_stdout = sys.stdout
            sys.stdout = DummyStdout()
            try:
                with self.assertRaises(SystemExit) as cm:
                    main()
            finally:
                sys.stdout = old_stdout

            # verify exit code and printed usage message
            self.assertEqual(cm.exception.code, 1)
            out = "".join(captured)
            self.assertIn("Usage: python diffs.py file1 file", out)
        finally:
            sys.argv[:] = old_argv
