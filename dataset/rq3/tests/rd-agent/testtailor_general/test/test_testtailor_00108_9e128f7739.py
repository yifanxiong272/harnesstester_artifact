import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.kaggle.experiment.templates.meta_tpl_deprecated.fea_share_preprocess')
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
        """Provide a synthetic DataFrame via monkeypatched pandas.read_csv so no file writes are needed."""
        pd = __import__("pandas")
        # Create a small synthetic dataset with 10 rows and 3 classes
        data = {
            "id": list(range(10)),
            "feature1": [i for i in range(10)],
            "feature2": [i * 2 for i in range(10)],
            "class": [("A", "B", "C")[i % 3] for i in range(10)],
        }
        df = pd.DataFrame(data)

        # Monkeypatch pandas.read_csv to return our synthetic DataFrame when the target path is requested
        original_read_csv = pd.read_csv
        pd.read_csv = lambda path: df.copy() if path == "/kaggle/input/train.csv" else original_read_csv(path)

        try:
            # Call the function under test
            try:
                X_train, X_valid, y_train, y_valid = prepreprocess()
            except Exception as e:
                self.fail(f"prepreprocess() raised an unexpected exception: {e!r}")
        finally:
            # Restore the original function to avoid side effects
            pd.read_csv = original_read_csv

        # Sanity checks on returned objects
        # Expect 10 rows total with test_size=0.10 -> 1 validation, 9 training
        self.assertEqual(len(X_train), 9)
        self.assertEqual(len(X_valid), 1)
        self.assertEqual(len(y_train), 9)
        self.assertEqual(len(y_valid), 1)

        # Ensure id and class columns are dropped from X
        self.assertNotIn("id", X_train.columns)
        self.assertNotIn("class", X_train.columns)

        # Ensure feature columns are present
        self.assertIn("feature1", X_train.columns)
        self.assertIn("feature2", X_train.columns)

        # Check that labels are numeric and we have three unique labels overall
        combined_labels = list(y_train) + list(y_valid)
        try:
            numeric_labels = [int(x) for x in combined_labels]
        except Exception:
            self.fail("Returned labels are not convertible to integers")
        self.assertEqual(len(set(numeric_labels)), 3)
