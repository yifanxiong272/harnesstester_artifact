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
        """Exercise run_from_cli for both the empty-directory early-return path
        and the successful merge+write path without relying on tempfile module.
        """
        base = Path.cwd() / f"tmp_run_from_cli_{id(self)}"
        # helper to recursively delete a path created by this test
        def _rmtree(p: Path):
            if not p.exists():
                return
            # remove children first
            children = list(p.rglob("*"))
            # sort so deeper paths are removed first
            children.sort(key=lambda x: len(x.parts), reverse=True)
            for child in children:
                try:
                    if child.is_file() or child.is_symlink():
                        child.unlink()
                    elif child.is_dir():
                        child.rmdir()
                except Exception:
                    pass
            try:
                if p.is_dir():
                    p.rmdir()
                elif p.exists():
                    p.unlink()
            except Exception:
                pass

        # Ensure clean start
        _rmtree(base)
        try:
            base.mkdir(parents=True, exist_ok=True)

            # 1) Empty directory: no .pred files -> merge_predictions should return
            # and not create a preds.json file.
            run_from_cli([str(base)])
            self.assertFalse((base / "preds.json").exists())

            # 2) Create a .pred file and request an explicit output file.
            subdir = base / "sub"
            subdir.mkdir()
            pred_file = subdir / "sample.pred"
            sample = {"instance_id": "inst1", "model_patch": None, "foo": 1}
            pred_file.write_text(json.dumps(sample))

            out_file = base / "out" / "merged.json"
            # Call the CLI entry with directory and explicit output path
            run_from_cli([str(base), "--output", str(out_file)])

            # Verify output file was written and contains the instance with model_patch normalized
            self.assertTrue(out_file.exists())
            merged = json.loads(out_file.read_text())
            self.assertIn("inst1", merged)
            self.assertEqual(merged["inst1"]["model_patch"], "")
        finally:
            # Clean up anything we created
            _rmtree(base)
