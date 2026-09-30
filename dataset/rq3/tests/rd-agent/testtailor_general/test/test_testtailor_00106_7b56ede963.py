import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.kaggle.experiment.templates.playground-series-s3e26.fea_share_preprocess')
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
        # Use dynamic imports so we don't rely on a specific module name at top-level
        pd = __import__('pandas')
        sys = __import__('sys')

        # Prepare small synthetic train and test DataFrames
        train_df = pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "Drug": ["A", "B", "A", "B", "A"],
            "Sex": ["M", "F", "F", "M", "M"],
            "Ascites": ["Y", "Y", "N", "N", "Y"],
            "Hepatomegaly": ["Yes", "No", "Yes", "No", "No"],
            "Spiders": ["Yes", "Yes", "No", "No", "Yes"],
            "Edema": ["Yes", "No", "No", "Yes", "No"],
            "Status": ["Alive", "Dead", "Alive", "Dead", "Alive"],
            "other": [10, 20, 30, 40, 50]
        })

        test_df = pd.DataFrame({
            "id": [10, 11],
            "Drug": ["A", "B"],
            "Sex": ["M", "F"],
            "Ascites": ["Y", "N"],
            "Hepatomegaly": ["Yes", "No"],
            "Spiders": ["No", "Yes"],
            "Edema": ["No", "Yes"],
            "other": [99, 100]
        })

        # Monkeypatch pandas.read_csv to return our DataFrames depending on the path
        orig_read_csv = pd.read_csv

        def fake_read_csv(path, *args, **kwargs):
            if str(path).endswith("train.csv"):
                return train_df.copy()
            if str(path).endswith("test.csv"):
                return test_df.copy()
            return orig_read_csv(path, *args, **kwargs)

        pd.read_csv = fake_read_csv

        try:
            # Locate the module that defines prepreprocess
            mod = None
            for m in list(sys.modules.values()):
                if m is not None and hasattr(m, "prepreprocess"):
                    mod = m
                    break
            # If not already loaded, try common module names
            if mod is None:
                for name in ("solution", "main", "app", "submission", "user_code", "script"):
                    try:
                        candidate = __import__(name)
                        if hasattr(candidate, "prepreprocess"):
                            mod = candidate
                            break
                    except Exception:
                        continue

            if mod is None:
                self.fail("Could not find a module with prepreprocess function to test.")

            prepreprocess = getattr(mod, "prepreprocess")

            X_train, X_valid, y_train, y_valid, X_test, status_encoder, test_ids = prepreprocess()

            # Basic checks on returned types
            self.assertIsInstance(X_train, pd.DataFrame)
            self.assertIsInstance(X_valid, pd.DataFrame)
            self.assertIsInstance(y_train, pd.Series)
            self.assertIsInstance(y_valid, pd.Series)
            self.assertIsInstance(X_test, pd.DataFrame)

            # test_ids should match ids from test_df
            self.assertListEqual(list(test_ids), list(test_df["id"]))

            # X_test shape should equal test_df without 'id'
            expected_X_test_shape = test_df.drop(["id"], axis=1).shape
            self.assertEqual(X_test.shape, expected_X_test_shape)

            # Status encoder should have classes equal to unique Status values in train_df
            self.assertSetEqual(set(status_encoder.classes_), set(train_df["Status"]))

            # Ensure categorical columns have been transformed to numeric (no object dtype)
            self.assertFalse(any(X_test.dtypes == "object"))

            # y_train should contain only integer encoded labels
            self.assertTrue(pd.api.types.is_integer_dtype(y_train.dtype) or pd.api.types.is_integer_dtype(y_train.values.dtype))

        finally:
            # Restore original read_csv
            pd.read_csv = orig_read_csv
