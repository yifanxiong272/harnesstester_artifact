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
        """Ensure predictions without 'model_patch' are skipped and do not appear in the merged output."""
        # use __import__ to avoid adding top-level import statements
        tempfile = __import__("tempfile")
        pathlib = __import__("pathlib")
        json = __import__("json")

        tmpdir = tempfile.TemporaryDirectory()
        try:
            Path = pathlib.Path
            d = Path(tmpdir.name)
            # create the directory just in case
            d.mkdir(parents=True, exist_ok=True)

            pred_file = d / "missing_model_patch.pred"
            pred_content = {"instance_id": "instance_missing_patch"}  # no 'model_patch' key
            pred_file.write_text(json.dumps(pred_content))

            # Call the function under test; output is None so it will write to d / "preds.json"
            merge_predictions([d], output=None)

            merged_file = d / "preds.json"
            # The function should have written an output file (empty dict because the only pred was skipped)
            self.assertTrue(merged_file.exists(), "Merged output file was not created")
            merged_data = json.loads(merged_file.read_text())
            self.assertEqual(merged_data, {}, "Merged data should be empty when all preds are skipped")
        finally:
            tmpdir.cleanup()
