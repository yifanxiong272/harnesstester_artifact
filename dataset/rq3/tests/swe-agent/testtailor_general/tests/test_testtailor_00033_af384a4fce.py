import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.extract_pred')
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
        """complete the test case here"""
        from pathlib import Path
        import tempfile
        import json

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            model_name = "modelA"
            instance_name = "instance42"
            # create nested directories: tmp/modelA/instance42/
            traj_dir = tmp_path / model_name / instance_name
            traj_dir.mkdir(parents=True, exist_ok=True)

            traj_path = traj_dir / "trajectory.json"
            data = {"info": {"submission": "patch-123"}}
            traj_path.write_text(json.dumps(data))

            # Call the function under test with the path as CLI arg
            run_from_cli([str(traj_path)])

            pred_path = traj_path.with_suffix(".pred")
            self.assertTrue(pred_path.exists(), "Prediction file was not created")

            pred_data = json.loads(pred_path.read_text())
            expected = {
                "model_name_or_path": traj_path.resolve().parent.parent.name,
                "model_patch": data["info"]["submission"],
                "instance_id": traj_path.resolve().parent.name,
            }
            self.assertEqual(pred_data, expected)
