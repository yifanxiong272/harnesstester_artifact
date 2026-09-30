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
        """Ensure old_filename is populated from the 'a/' path when a and b differ
        and there is no explicit 'rename from' metadata in the diff section."""
        diff = (
            "diff --git a/src/old_name.py b/src/new_name.py\n"
            "index 1234567..89abcde 100644\n"
            "--- a/src/old_name.py\n"
            "+++ b/src/new_name.py\n"
            "@@ -1 +1 @@\n"
            "-old_line\n"
            "+new_line\n"
        )

        files = parse_unified_diff(diff)
        # One file section should be parsed
        self.assertEqual(len(files), 1)
        f = files[0]
        # filename should be taken from the b/ path
        self.assertEqual(f.filename, "src/new_name.py")
        # old_filename should be set to the a/ path because a != b and no rename info
        self.assertEqual(f.old_filename, "src/old_name.py")
        # Sanity: base/head reconstruction worked for the simple hunk
        self.assertIn("old_line", f.base_file)
        self.assertIn("new_line", f.head_file)
