import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.kaggle.experiment.templates.sf-crime.fea_share_preprocess')
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
        """Test prepreprocess with synthetic train/test CSV content by monkeypatching pd.read_csv."""
        # Prepare synthetic data matching expected columns.
        # Ensure insertion order places 'Category' before 'Dates' so slicing train.columns[2:12] does NOT include 'Category'.
        dates = pd.date_range("2020-01-01", periods=10, freq="H")
        train_df = pd.DataFrame(
            {
                "Id": list(range(10)),
                "Category": ["THEFT", "BURGLARY"] * 5,
                "Dates": dates,
                "PdDistrict": ["NORTHERN", "BAY"] * 5,
                "X": [float(i) for i in range(10)],
                "Y": [float(i) + 0.5 for i in range(10)],
                "Descript": ["desc"] * 10,
                "Resolution": ["res"] * 10,
                "Address": ["addr"] * 10,
            }
        )
        # Test dataframe does not include 'Category' (as in real test set)
        test_df = pd.DataFrame(
            {
                "Id": list(range(100, 110)),
                "Dates": dates,
                "PdDistrict": ["NORTHERN", "BAY"] * 5,
                "X": [float(i) for i in range(10)],
                "Y": [float(i) + 0.5 for i in range(10)],
                "Address": ["addr"] * 10,
            }
        )

        # Monkeypatch pd.read_csv to return our synthetic dataframes when expected paths are used
        orig_read_csv = pd.read_csv

        def fake_read_csv(path, parse_dates=None, index_col=None, **kwargs):
            p = str(path)
            if p.endswith("/train.csv") or p.endswith("train.csv"):
                df = train_df.copy()
                df["Dates"] = pd.to_datetime(df["Dates"])
                return df
            if p.endswith("/test.csv") or p.endswith("test.csv"):
                df = test_df.copy()
                df["Dates"] = pd.to_datetime(df["Dates"])
                return df
            return orig_read_csv(path, parse_dates=parse_dates, index_col=index_col, **kwargs)

        pd.read_csv = fake_read_csv

        try:
            result = prepreprocess()
            # Expect 7 return values as per function signature
            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 7)

            X_train, X_valid, y_train, y_valid, X_test, category_encoder, test_ids = result

            # Basic sanity checks on returned objects
            self.assertTrue(hasattr(X_train, "shape"))
            self.assertTrue(hasattr(X_valid, "shape"))
            # y_train and y_valid lengths should sum to original train length
            self.assertEqual(len(y_train) + len(y_valid), len(train_df))
            # X_test should be dataframe-like
            self.assertTrue(hasattr(X_test, "shape"))
            # Category encoder should expose classes_
            self.assertTrue(hasattr(category_encoder, "classes_"))
            classes = set(category_encoder.classes_)
            self.assertEqual(classes, {"THEFT", "BURGLARY"})
            # test_ids should match test_df['Id']
            pd.testing.assert_series_equal(test_ids.reset_index(drop=True), test_df["Id"].reset_index(drop=True))

            # Ensure 'Minute' was removed from feature columns as intended
            self.assertNotIn("Minute", X_train.columns)
            # Ensure PdDistrict was encoded (numeric dtype)
            self.assertTrue(pd.api.types.is_numeric_dtype(X_train["PdDistrict"].dtype))
            self.assertTrue(pd.api.types.is_numeric_dtype(X_test["PdDistrict"].dtype))
        finally:
            pd.read_csv = orig_read_csv
