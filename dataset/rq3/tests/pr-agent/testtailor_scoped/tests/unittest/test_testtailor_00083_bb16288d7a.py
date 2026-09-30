import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.mosaico.dispatch')
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
    def test_diff_header_splits_text(self):
        """Ensure prose before an unfenced diff/hunk header is returned and the diff body removed."""
        text = (
            "What changed here?\n"
            "Please review the following change.\n"
            "\n"
            "diff --git a/foo.py b/foo.py\n"
            "index 1111111..2222222 100644\n"
            "--- a/foo.py\n"
            "+++ b/foo.py\n"
            "@@ -1,2 +1,2 @@\n"
            "-x = 1\n"
            "+x = 2\n"
            " y = 3\n"
        )

        result = _diff_prose(text)

        # The result should be exactly the portion before the first "diff --git ..." header.
        expected = text[: text.index("diff --git a/foo.py b/foo.py")]
        self.assertEqual(result, expected)

        # Sanity checks: prose preserved (including the question mark) and no diff header present.
        self.assertIn("What changed here?", result)
        self.assertNotIn("diff --git", result)
        self.assertNotIn("@@ -1,2 +1,2 @@", result)
