import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.kaggle.experiment.templates.playground-series-s4e5.fea_share_preprocess')
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
        # create a synthetic DataFrame with required columns
        n = 20
        records = [
            {"id": i, "feat1": float(i), "feat2": i + 0.5, "FloodProbability": i % 5}
            for i in range(n)
        ]
        df = pd.DataFrame.from_records(records)

        # Patch pandas.read_csv to return our synthetic dataframe
        with unittest.mock.patch("pandas.read_csv", return_value=df) as mock_read:
            X_train, X_valid, y_train, y_valid = prepreprocess()

            # ensure read_csv was called with the expected path
            mock_read.assert_called_once_with("/kaggle/input/train.csv")

            # basic sanity checks on returned objects
            self.assertIsInstance(X_train, pd.DataFrame)
            self.assertIsInstance(X_valid, pd.DataFrame)
            self.assertIsInstance(y_train, pd.Series)
            self.assertIsInstance(y_valid, pd.Series)

            # total rows preserved across splits
            self.assertEqual(len(X_train) + len(X_valid), n)
            self.assertEqual(len(y_train) + len(y_valid), n)

            # 'id' must have been dropped and feature columns preserved
            self.assertNotIn("id", X_train.columns)
            self.assertIn("feat1", X_train.columns)
            self.assertIn("feat2", X_train.columns)

            # target values should come from original FloodProbability values
            original_targets = set(df["FloodProbability"].unique())
            self.assertTrue(set(y_train.unique()).issubset(original_targets))
            self.assertTrue(set(y_valid.unique()).issubset(original_targets))
