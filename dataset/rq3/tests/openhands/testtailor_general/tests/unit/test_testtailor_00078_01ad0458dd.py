import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.resolver.patching.apply')
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
        """Ensure that when the external 'patch' program cannot be found we raise the expected SubprocessException."""
        original_content = "# PR Viewer\n\nSimple file content\n"
        patch = """diff --git a/README.md b/README.md
index b760a53..5071727 100644
--- a/README.md
+++ b/README.md
@@ -1,3 +1,3 @@
 # PR Viewer

-Simple file content
+Modified content
"""

        # Build a minimal diff-like object expected by apply_diff/_apply_diff_with_subprocess
        class DummyDiff:
            pass

        diff = DummyDiff()
        diff.header = None
        diff.text = patch

        # Patch the which lookup in the module so it behaves as if 'patch' is not installed
        with unittest.mock.patch('openhands.resolver.patching.apply.which', return_value=None):
            with self.assertRaises(SubprocessException) as cm:
                apply_diff(diff, original_content, use_patch=True)

        exc = cm.exception
        self.assertEqual(exc.code, -1)
        self.assertIn('cannot find patch program', str(exc))
