import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.kaggle.experiment.utils')
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
        import tempfile
        import sys
        import importlib
        from pathlib import Path
        import json

        # locate the function under test in loaded modules or try common module names
        func = globals().get("python_files_to_notebook", None)
        if func is None:
            for m in list(sys.modules.values()):
                try:
                    if hasattr(m, "python_files_to_notebook"):
                        func = getattr(m, "python_files_to_notebook")
                        break
                except Exception:
                    continue
        if func is None:
            for candidate in ("solution", "submission", "user_code", "main", "__main__"):
                try:
                    mod = importlib.import_module(candidate)
                    if hasattr(mod, "python_files_to_notebook"):
                        func = getattr(mod, "python_files_to_notebook")
                        break
                except Exception:
                    continue

        if func is None:
            self.fail("Could not find python_files_to_notebook function to test")

        # Create temporary project structure required by the function
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            # pre file
            pre_file = base / "fea_share_preprocess.py"
            pre_file.write_text("DATA_PATH = '/kaggle/input'\n", encoding="utf-8")

            # feature directory and one feature file
            feat_dir = base / "feature"
            feat_dir.mkdir()
            feat1 = feat_dir / "feat1.py"
            # contains the name that will be replaced: feature_engineering_cls
            feat1.write_text(
                "def feature_engineering_cls():\n"
                "    return 'feat1'\n",
                encoding="utf-8",
            )

            # model directory and one model file
            model_dir = base / "model"
            model_dir.mkdir()
            model_a = model_dir / "modelA.py"
            model_a.write_text(
                "def fit(X, y):\n"
                "    pass\n\n"
                "def predict(X):\n"
                "    return []\n",
                encoding="utf-8",
            )

            # select file corresponding to the model
            select_a = model_dir / "selectA.py"
            select_a.write_text(
                "def select(x):\n"
                "    return x\n",
                encoding="utf-8",
            )

            # train.py containing the exact strings the function replaces
            train = base / "train.py"
            train.write_text(
                "from fea_share_preprocess import preprocess_script\n"
                "DIRNAME = Path(__file__).absolute().resolve().parent\n\n"
                "for f in DIRNAME.glob(\"feature/feat*.py\"):\n"
                "    cls = import_module_from_path(f.stem, f).feature_engineering_cls()\n\n"
                "for f in DIRNAME.glob(\"model/model*.py\"):\n"
                "    m = import_module_from_path(f.stem, f)\n"
                "    select_python_path = f.with_name(f.stem.replace(\"model\", \"select\") + f.suffix)\n"
                "    select_m = import_module_from_path(select_python_path.stem, select_python_path)\n"
                "    a = [2].select\n",
                encoding="utf-8",
            )

            # Call the function under test
            comp_name = "comp123"
            # function accepts either Path or str for py_dir
            func(comp_name, str(base))

            merged_py = base / "merged.py"
            merged_ipynb = base / "merged.ipynb"

            # Assert files are created
            self.assertTrue(merged_py.exists(), "merged.py was not created")
            self.assertTrue(merged_ipynb.exists(), "merged.ipynb was not created")

            merged_text = merged_py.read_text(encoding="utf-8")

            # Check that the preprocess path was replaced with competition name
            self.assertIn(f"/kaggle/input/{comp_name}", merged_text)

            # Check that feature function name was replaced and a call was appended
            self.assertIn("def feat1_cls", merged_text)
            self.assertIn("feat1_cls()", merged_text)

            # Check that model file got converted into a class named after its stem
            self.assertIn("class modelA:", merged_text)

            # Check that select function was renamed to its file stem (selectA)
            self.assertIn("def selectA(", merged_text)

            # Check that the train loop for features was rewritten to iterate over cls list
            self.assertIn("for cls in [", merged_text)

            # Inspect ipynb to ensure it is a JSON notebook with cells present
            nb_text = merged_ipynb.read_text(encoding="utf-8")
            try:
                nb_json = json.loads(nb_text)
                self.assertIn("cells", nb_json)
                # At least 1 cell should exist (pre + others)
                self.assertTrue(len(nb_json.get("cells", [])) >= 1)
            except Exception as e:
                self.fail(f"merged.ipynb is not valid JSON notebook: {e}")
