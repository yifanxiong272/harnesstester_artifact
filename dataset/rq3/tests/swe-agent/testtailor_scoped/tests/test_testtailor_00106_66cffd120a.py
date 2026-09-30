import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.utils.patch_formatter')
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
        """Ensure _get_hunk_lines uses source_start and source_length when original=True."""
        # A minimal unified diff with a single modified file and a single hunk.
        patch = """--- a/test.txt
+++ b/test.txt
@@ -3,2 +3,2 @@
 context line
-line-old
+line-new
"""
        # read_method won't be used for original=True when calling _get_hunk_lines directly,
        # but PatchFormatter.__init__ will call it for patched files, so provide a simple lambda.
        pf = PatchFormatter(patch, lambda p: "")
        # Use context_length=2 so:
        # start = max(1, source_start - 2) => max(1, 3 - 2) == 1
        # stop = source_start + source_length + 2 => 3 + 2 + 2 == 7
        hunk_lines = pf._get_hunk_lines(original=True, context_length=2)
        # Expect exactly one file entry
        self.assertEqual(len(hunk_lines), 1)
        starts, stops = next(iter(hunk_lines.values()))
        self.assertEqual(starts, [1])
        self.assertEqual(stops, [7])
