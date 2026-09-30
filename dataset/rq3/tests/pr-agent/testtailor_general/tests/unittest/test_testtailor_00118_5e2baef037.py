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
        """If diff header names differ (a/... != b/...) and there are no rename lines,
        parse_unified_diff should set old_filename to the a/ path.
        """
        diff = (
            "diff --git a/old_name.py b/new_name.py\n"
            "index 1111111..2222222 100644\n"
            "--- a/old_name.py\n"
            "+++ b/new_name.py\n"
            "@@ -1 +1 @@\n"
            "-print('old')\n"
            "+print('new')\n"
        )

        files = parse_unified_diff(diff)
        # One file section should be parsed
        self.assertEqual(len(files), 1)
        f = files[0]
        # filename should be the b/ path, and old_filename should be set to the a/ path
        self.assertEqual(f.filename, "new_name.py")
        self.assertEqual(f.old_filename, "old_name.py")
        # verify reconstructed contents include the expected lines
        self.assertIn("print('old')", f.base_file)
        self.assertIn("print('new')", f.head_file)
