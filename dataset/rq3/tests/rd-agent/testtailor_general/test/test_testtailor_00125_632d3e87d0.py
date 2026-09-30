import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.kaggle.experiment.templates.new-york-city-taxi-fare-prediction.fea_share_preprocess')
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
        """Test prepreprocess reads CSV, drops index and label, and splits correctly."""
        # Build a small DataFrame simulating /kaggle/input/train.csv
        df = pd.DataFrame({
            "key": ["k1", "k2", "k3", "k4", "k5"],
            "fare_amount": [10.0, 20.0, 30.0, 40.0, 50.0],
            "passenger_count": [1, 2, 1, 3, 2],
            "distance": [0.5, 1.2, 0.7, 2.0, 1.1]
        })

        # Patch pandas.read_csv to return our DataFrame
        with unittest.mock.patch("pandas.read_csv", return_value=df) as mock_read:
            X_train, X_valid, y_train, y_valid = prepreprocess()

            # Ensure read_csv was called with the expected path
            mock_read.assert_called_once_with("/kaggle/input/train.csv")

            # Combined lengths should equal original
            self.assertEqual(len(X_train) + len(X_valid), len(df))
            self.assertEqual(len(y_train) + len(y_valid), len(df))

            # The index column "key" should be dropped from features
            self.assertNotIn("key", X_train.columns)
            self.assertNotIn("key", X_valid.columns)

            # The label should be removed from X and returned as y
            self.assertNotIn("fare_amount", X_train.columns)
            self.assertEqual(sorted(list(X_train.columns)), sorted(["passenger_count", "distance"]))

            # Types
            self.assertIsInstance(X_train, pd.DataFrame)
            self.assertIsInstance(X_valid, pd.DataFrame)
            self.assertIsInstance(y_train, pd.Series)
            self.assertIsInstance(y_valid, pd.Series)

            # With 5 samples and test_size=0.20 expect 1 sample in validation
            self.assertEqual(len(X_valid), 1)
            self.assertEqual(len(y_valid), 1)

            # Ensure y values come from the original fare_amount column
            self.assertTrue(set(y_train).issubset(set(df["fare_amount"])))
            self.assertTrue(set(y_valid).issubset(set(df["fare_amount"])))
