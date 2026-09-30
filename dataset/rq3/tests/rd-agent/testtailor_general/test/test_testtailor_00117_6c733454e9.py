import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.kaggle.experiment.templates.playground-series-s4e9.fea_share_preprocess')
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
        # create a small dataframe that matches what prepreprocess expects
        df = pd.DataFrame({
            "id": list(range(10)),
            "price": list(range(100, 110)),
            "feature": list(range(10, 20))
        })

        # patch pd.read_csv to return our dataframe regardless of path
        orig_read_csv = pd.read_csv
        pd.read_csv = lambda path: df.copy()

        try:
            X_train, X_valid, y_train, y_valid = prepreprocess()

            # total rows preserved
            self.assertEqual(len(X_train) + len(X_valid), len(df))
            self.assertEqual(len(y_train) + len(y_valid), len(df))

            # with test_size=0.10 on 10 rows, 1 row should be in validation
            self.assertEqual(len(X_valid), 1)
            self.assertEqual(len(y_valid), 1)
            self.assertEqual(len(X_train), 9)
            self.assertEqual(len(y_train), 9)

            # 'id' should be dropped from features
            self.assertNotIn("id", X_train.columns)
            self.assertNotIn("id", X_valid.columns)

            # 'price' should not be in X (it's y)
            self.assertNotIn("price", X_train.columns)
            self.assertNotIn("price", X_valid.columns)

            # y should contain only values from the original price column
            original_prices = set(df["price"])
            self.assertTrue(set(y_train).issubset(original_prices))
            self.assertTrue(set(y_valid).issubset(original_prices))
        finally:
            # restore original read_csv
            pd.read_csv = orig_read_csv
