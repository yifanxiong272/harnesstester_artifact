import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.mosaico.diff_provider')
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
        """parse_unified_diff must ignore '\ No newline' marker lines in hunks."""
        diff = (
            "diff --git a/foo.txt b/foo.txt\n"
            "index 1111111..2222222 100644\n"
            "--- a/foo.txt\n"
            "+++ b/foo.txt\n"
            "@@ -1,1 +1,1 @@\n"
            "-hello\n"
            "\\ No newline at end of file\n"
            "+hello world\n"
            "\\ No newline at end of file\n"
        )

        files = parse_unified_diff(diff)
        self.assertEqual(len(files), 1)

        f = files[0]
        # filename should come from the b/ path
        self.assertEqual(f.filename, "foo.txt")
        # The '\ No newline' lines are skipped; content reconstructed from +/- lines only
        self.assertEqual(f.base_file, "hello\n")
        self.assertEqual(f.head_file, "hello world\n")
        # patch should contain the original diff text
        self.assertIn("No newline", f.patch)
