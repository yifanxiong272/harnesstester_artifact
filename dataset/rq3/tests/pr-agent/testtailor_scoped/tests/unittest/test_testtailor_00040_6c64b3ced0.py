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
        """A deleted-file diff yields EDIT_TYPE.DELETED and reconstructs base content."""
        diff = (
            "diff --git a/removed.txt b/removed.txt\n"
            "deleted file mode 100644\n"
            "index 4b825dc..0000000\n"
            "--- a/removed.txt\n"
            "+++ /dev/null\n"
            "@@ -1,3 +0,0 @@\n"
            "-line1\n"
            "-line2\n"
            "-line3\n"
        )

        files = parse_unified_diff(diff)
        # One file section should be parsed
        self.assertEqual(len(files), 1)
        f = files[0]

        # filename comes from the b/ path captured by the diff header regex
        self.assertEqual(f.filename, "removed.txt")
        # edit_type must be detected as DELETED
        self.assertEqual(f.edit_type, EDIT_TYPE.DELETED)
        # head_file should be empty for a deletion
        self.assertEqual(f.head_file, "")
        # base_file reconstructed from '-' hunk lines
        self.assertEqual(f.base_file, "line1\nline2\nline3\n")
        # no rename info expected
        self.assertIsNone(f.old_filename)
