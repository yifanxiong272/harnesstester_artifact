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
        """When output is None, merge_predictions should write to directories[0]/preds.json"""
        tmpmod = __import__("tempfile")
        pathlib = __import__("pathlib")
        json = __import__("json")

        with tmpmod.TemporaryDirectory() as td:
            base = pathlib.Path(td) / "preds_dir"
            base.mkdir()
            # create a single .pred file with required fields
            pred_file = base / "example.pred"
            content = {"instance_id": "inst_1", "model_patch": "patch_v1", "value": 42}
            pred_file.write_text(json.dumps(content))
            # Call function under test with output=None (explicitly)
            merge_predictions([base], output=None)
            # Expect output at base / "preds.json"
            out_file = base / "preds.json"
            self.assertTrue(out_file.exists(), f"Expected merged file at {out_file}")
            merged = json.loads(out_file.read_text())
            # merged should be a dict with our instance_id as a key
            self.assertIn("inst_1", merged)
            self.assertEqual(merged["inst_1"]["model_patch"], "patch_v1")
            self.assertEqual(merged["inst_1"]["value"], 42)
