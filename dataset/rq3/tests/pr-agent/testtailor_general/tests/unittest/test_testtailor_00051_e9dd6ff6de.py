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
        """parse_unified_diff should mark a file with 'deleted file mode' as EDIT_TYPE.DELETED
        and reconstruct the base/head contents appropriately."""
        diff_text = (
            "diff --git a/foo.txt b/foo.txt\n"
            "deleted file mode 100644\n"
            "index 1111111..0000000 100644\n"
            "--- a/foo.txt\n"
            "+++ /dev/null\n"
            "@@ -1 +0,0 @@\n"
            "-hello\n"
        )

        files = parse_unified_diff(diff_text)
        # One file section should be returned
        self.assertEqual(len(files), 1)

        f = files[0]
        # The edit type should be detected as DELETED
        self.assertEqual(f.edit_type, EDIT_TYPE.DELETED)
        # Filename should be taken from the b/ path captured by the header regex
        self.assertEqual(f.filename, "foo.txt")
        # The base file content should contain the removed line, head file should be empty
        self.assertEqual(f.base_file, "hello\n")
        self.assertEqual(f.head_file, "")
        # old_filename should remain None for a plain deletion (no rename)
        self.assertIsNone(f.old_filename)
