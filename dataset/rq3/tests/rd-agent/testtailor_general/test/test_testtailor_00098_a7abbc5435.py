import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.kaggle.experiment.templates.optiver-realized-volatility-prediction.fea_share_preprocess')
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
        import pandas as pd
        import sys

        # locate the module that defines prepreprocess
        target_mod = None
        for m in list(sys.modules.values()):
            if m is None:
                continue
            if hasattr(m, "prepreprocess"):
                target_mod = m
                break
        self.assertIsNotNone(target_mod, "Could not find module with 'prepreprocess' function")

        # Prepare fake dataframes that mimic the expected files
        train_df = pd.DataFrame({
            "stock_id": [1, 2],
            "time_id": [10, 20],
            "target": [0.5, -0.3]
        })
        book_train = pd.DataFrame({
            "stock_id": [1, 2],
            "time_id": [10, 20],
            "book_col": [100, 200]
        })
        trade_train = pd.DataFrame({
            "stock_id": [1, 2],
            "time_id": [10, 20],
            "trade_col": [1.1, 2.2]
        })

        # Patch the pandas read functions used inside the target module
        def fake_read_csv(path, *args, **kwargs):
            # only one CSV in the code: train.csv
            return train_df.copy()

        def fake_read_parquet(path, *args, **kwargs):
            # differentiate by filename
            if "book" in path:
                return book_train.copy()
            if "trade" in path:
                return trade_train.copy()
            # default to empty
            return pd.DataFrame()

        # Simple deterministic train_test_split that returns first row as train, second as valid
        def fake_train_test_split(X, y, test_size, random_state):
            X_train = X.iloc[[0]]
            X_valid = X.iloc[[1]]
            y_train = y.iloc[[0]]
            y_valid = y.iloc[[1]]
            return X_train, X_valid, y_train, y_valid

        # Inject our fakes into the target module
        # target_mod.pd is the pandas module used inside the function
        target_mod.pd.read_csv = fake_read_csv
        target_mod.pd.read_parquet = fake_read_parquet
        # override train_test_split used inside the module if present
        target_mod.train_test_split = fake_train_test_split

        # Call the function under test
        result = target_mod.prepreprocess()

        # Validate the returned objects
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 4)
        X_train, X_valid, y_train, y_valid = result

        # Basic structure checks
        self.assertTrue(hasattr(X_train, "columns"))
        self.assertTrue(hasattr(X_valid, "columns"))

        # Should have merged book and trade columns and dropped 'target'
        self.assertIn("book_col", X_train.columns.tolist())
        self.assertIn("trade_col", X_train.columns.tolist())
        self.assertNotIn("target", X_train.columns.tolist())

        # Because our fake split returns one row each
        self.assertEqual(len(X_train), 1)
        self.assertEqual(len(X_valid), 1)
