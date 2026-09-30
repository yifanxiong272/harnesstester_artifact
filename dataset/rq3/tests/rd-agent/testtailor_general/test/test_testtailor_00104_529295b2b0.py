import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.kaggle.experiment.templates.playground-series-s4e8.fea_share_preprocess')
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
        """Test that prepreprocess reads the CSV, drops 'id', encodes labels and splits correctly."""
        # Create a small dummy dataframe with 10 rows so test_size=0.10 -> 1 validation sample
        df = pd.DataFrame({
            "id": list(range(10)),
            "feature1": list(range(10)),
            "feature2": [i * 2 for i in range(10)],
            "class": ["A", "B", "A", "C", "B", "A", "C", "B", "A", "C"]
        })

        # Patch pandas.read_csv to return our dummy dataframe
        with unittest.mock.patch("pandas.read_csv", return_value=df):
            X_train, X_valid, y_train, y_valid = prepreprocess()

        # Check that id column was dropped and only feature columns remain
        self.assertListEqual(list(X_train.columns), ["feature1", "feature2"])
        self.assertListEqual(list(X_valid.columns), ["feature1", "feature2"])

        # Check split sizes: 10 total -> 9 train, 1 valid with test_size=0.10
        self.assertEqual(X_train.shape[0], 9)
        self.assertEqual(X_valid.shape[0], 1)
        self.assertEqual(len(y_train), 9)
        self.assertEqual(len(y_valid), 1)

        # Check that labels are numeric (encoded) and within the expected range {0,1,2}
        combined = list(y_train) + list(y_valid)
        unique_labels = set(int(x) for x in combined)
        self.assertTrue(unique_labels.issubset({0, 1, 2}))
