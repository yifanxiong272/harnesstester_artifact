import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.kaggle.experiment.templates.statoil-iceberg-classifier-challenge.fea_share_preprocess')
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
        """Test prepreprocess processes train/test JSONs correctly and returns expected splits."""
        # Prepare synthetic data matching expected structure
        n_train = 5
        n_test = 2
        size = 75 * 75

        train_ids = [f"train_{i}" for i in range(n_train)]
        test_ids = [f"test_{i}" for i in range(n_test)]

        # create distinct band arrays for each row
        train_band_1 = [(np.arange(size) + i).astype(float).tolist() for i in range(n_train)]
        train_band_2 = [((np.arange(size) + i * 2) * 0.5).astype(float).tolist() for i in range(n_train)]
        # include one "na" inc_angle to test replacement
        train_inc = ["na", 30.0, 35.0, 40.0, 45.0]
        train_is_iceberg = [0, 1, 0, 1, 0]

        train_df = pd.DataFrame({
            "id": train_ids,
            "band_1": train_band_1,
            "band_2": train_band_2,
            "inc_angle": train_inc,
            "is_iceberg": train_is_iceberg
        })

        test_band_1 = [(np.arange(size) + 100 + i).astype(float).tolist() for i in range(n_test)]
        test_band_2 = [((np.arange(size) + 200 + i) * 0.2).astype(float).tolist() for i in range(n_test)]
        test_inc = [25.0, "na"]

        test_df = pd.DataFrame({
            "id": test_ids,
            "band_1": test_band_1,
            "band_2": test_band_2,
            "inc_angle": test_inc
        })

        # Patch pd.read_json to return our synthetic DataFrames
        original_read_json = pd.read_json

        def fake_read_json(path):
            if "train.json" in path:
                return train_df.copy()
            if "test.json" in path:
                return test_df.copy()
            return original_read_json(path)

        pd.read_json = fake_read_json

        try:
            # Call the function under test
            X_train, X_valid, y_train, y_valid, X_test, returned_test_ids = prepreprocess()

            # Expected feature columns after processing and dropping bands/is_iceberg
            expected_cols = {
                "band_1_mean", "band_2_mean", "band_3_mean",
                "band_1_max", "band_2_max", "band_3_max",
                "inc_angle"
            }

            # Verify columns
            self.assertEqual(set(X_train.columns), expected_cols)
            self.assertEqual(set(X_valid.columns), expected_cols)
            self.assertEqual(set(X_test.columns), expected_cols)

            # Check that total rows equal original train rows split
            self.assertEqual(len(X_train) + len(X_valid), n_train)
            # y lengths correspond
            self.assertEqual(len(y_train) + len(y_valid), n_train)

            # Test ids returned match input test ids
            self.assertListEqual(list(returned_test_ids), test_ids)

            # Ensure no missing inc_angle remains
            self.assertEqual(X_train["inc_angle"].isnull().sum(), 0)
            self.assertEqual(X_valid["inc_angle"].isnull().sum(), 0)
            self.assertEqual(X_test["inc_angle"].isnull().sum(), 0)

            # Validate numeric feature computation for one of the test rows (index 0)
            # Compute expected means and max from original test data
            expected_band1_mean = np.mean(test_band_1[0])
            expected_band2_mean = np.mean(test_band_2[0])
            expected_band3_mean = (expected_band1_mean + expected_band2_mean) / 2.0
            expected_band1_max = np.max(test_band_1[0])
            expected_band2_max = np.max(test_band_2[0])
            expected_band3_max = np.max((np.array(test_band_1[0]) + np.array(test_band_2[0])) / 2.0)

            # Find the corresponding row in X_test for test index 0
            row0 = X_test.iloc[0]
            self.assertAlmostEqual(row0["band_1_mean"], expected_band1_mean, places=6)
            self.assertAlmostEqual(row0["band_2_mean"], expected_band2_mean, places=6)
            self.assertAlmostEqual(row0["band_3_mean"], expected_band3_mean, places=6)
            self.assertAlmostEqual(row0["band_1_max"], expected_band1_max, places=6)
            self.assertAlmostEqual(row0["band_2_max"], expected_band2_max, places=6)
            self.assertAlmostEqual(row0["band_3_max"], expected_band3_max, places=6)

        finally:
            # Restore original function to avoid side effects
            pd.read_json = original_read_json
