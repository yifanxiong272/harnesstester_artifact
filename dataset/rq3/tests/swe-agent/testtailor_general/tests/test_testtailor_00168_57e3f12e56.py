import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.merge_predictions')
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
        """Test that merge_predictions raises on duplicate instance IDs."""
        # Use dynamic imports to avoid top-level import statements
        tempfile = __import__("tempfile")
        pathlib = __import__("pathlib")
        json = __import__("json")

        Path = pathlib.Path

        # Create two temporary directories each containing a .pred file with the same instance_id
        with tempfile.TemporaryDirectory() as dir1, tempfile.TemporaryDirectory() as dir2:
            p1 = Path(dir1) / "pred1.pred"
            p2 = Path(dir2) / "pred2.pred"
            payload = {"instance_id": "dup_id", "model_patch": "patch_content"}
            p1.write_text(json.dumps(payload))
            p2.write_text(json.dumps(payload))

            # Expect a ValueError indicating a duplicate instance ID
            with self.assertRaisesRegex(ValueError, r"Duplicate instance ID found: dup_id"):
                merge_predictions([Path(dir1), Path(dir2)], output=None)
