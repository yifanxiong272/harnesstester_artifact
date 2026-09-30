import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.resolver.patching.patch')
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
        """Ensure parse_scm_header strips a/ from old_path when a git diff header is present."""
        text = """diff --git a/example.py b/example.py
Index: a/example.py
diff -u a/example.py:1.1 b/example.py:1.2
--- a/example.py
+++ b/example.py
@@ -1 +1 @@
-old line
+new line
"""
        res = parse_scm_header(text)
        self.assertIsNotNone(res)
        # parse_cvs_header will return old_path as 'a/example.py' which
        # parse_scm_header should strip to 'example.py' when git diff is present.
        self.assertEqual(res.old_path, 'example.py')
        self.assertEqual(res.new_path, 'example.py')
