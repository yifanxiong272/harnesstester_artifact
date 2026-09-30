import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.run_traj_to_demo')
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
        """Raise FileExistsError when the output file already exists and overwrite is False."""
        # Create a unique temporary directory under the current working directory to avoid using tempfile
        tmp = Path.cwd() / f"tmp_test_{id(self)}"
        tmp.mkdir(exist_ok=True)
        try:
            # create a trajectory file in a parent folder
            traj_parent = tmp / "traj_parent"
            traj_parent.mkdir(exist_ok=True)
            traj_file = traj_parent / "session.traj"
            traj_file.write_text("{}")

            # choose an output_dir and pre-create the output file that main() would generate
            output_dir = tmp / "outdir"
            output_file = output_dir / (traj_file.parent.name + "") / (traj_file.stem.removesuffix(".traj") + ".demo.yaml")
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text("already exists")

            expected_msg = f"Output file already exists: {output_file}. Use --overwrite to overwrite."
            with self.assertRaises(FileExistsError) as cm:
                main(traj_file, output_dir, suffix="", overwrite=False)
            self.assertEqual(str(cm.exception), expected_msg)
        finally:
            # best-effort cleanup
            try:
                if output_file.exists():
                    output_file.unlink()
            except Exception:
                pass
            try:
                if output_file.parent.exists():
                    output_file.parent.rmdir()
            except Exception:
                pass
            try:
                if output_dir.exists():
                    output_dir.rmdir()
            except Exception:
                pass
            try:
                if traj_file.exists():
                    traj_file.unlink()
            except Exception:
                pass
            try:
                if traj_parent.exists():
                    traj_parent.rmdir()
            except Exception:
                pass
            try:
                if tmp.exists():
                    tmp.rmdir()
            except Exception:
                pass
