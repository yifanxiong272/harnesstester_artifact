import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.kaggle.experiment.templates.tabular-playground-series-dec-2021.fea_share_preprocess')
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
        # Prepare a small synthetic dataframe that matches expected CSV structure
        df = pd.DataFrame({
            "Id": list(range(1, 11)),
            "Feat1": [0.1 * i for i in range(10)],
            "Feat2": [i % 3 for i in range(10)],
            "Cover_Type": [1, 2, 3, 1, 2, 3, 1, 2, 3, 1]  # values in 1..3 as expected by code
        })

        # Monkeypatch pd.read_csv so prepreprocess reads our DataFrame instead of a file
        original_read_csv = pd.read_csv
        pd.read_csv = lambda path: df.copy()

        try:
            # Call the function under test
            X_train, X_valid, y_train, y_valid = prepreprocess()

            # Basic shape checks: train + valid should equal original rows
            total_rows = len(X_train) + len(X_valid)
            self.assertEqual(total_rows, len(df))

            # Validation size should be 20% of 10 -> 2
            self.assertEqual(len(X_valid), 2)
            self.assertEqual(len(y_valid), 2)

            # Columns: Id should be dropped, Cover_Type should not be in X
            expected_feature_cols = ["Feat1", "Feat2"]
            self.assertListEqual(list(X_train.columns), expected_feature_cols)
            self.assertListEqual(list(X_valid.columns), expected_feature_cols)
            self.assertNotIn("Id", X_train.columns)
            self.assertNotIn("Cover_Type", X_train.columns)

            # y values should be original Cover_Type minus 1 (so in 0..2)
            all_y_values = list(y_train) + list(y_valid)
            self.assertTrue(all(0 <= v <= 2 for v in all_y_values))
            # Check that the multiset of labels matches original Cover_Type shifted by -1
            expected_labels = [v - 1 for v in df["Cover_Type"].tolist()]
            self.assertCountEqual(all_y_values, expected_labels)

        finally:
            # Restore original read_csv to avoid side effects on other tests
            pd.read_csv = original_read_csv
