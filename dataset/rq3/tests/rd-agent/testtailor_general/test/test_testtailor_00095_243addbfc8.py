import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.kaggle.experiment.templates.spaceship-titanic.fea_share_preprocess')
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
        import numpy as np
        from unittest.mock import patch

        # Create a small synthetic DataFrame that matches expected input
        n_samples = 10
        df = pd.DataFrame({
            "PassengerId": list(range(1000, 1000 + n_samples)),
            "Age": np.arange(n_samples) + 20,
            "Transported": [True, False] * (n_samples // 2)
        })

        # Patch pandas.read_csv so the function reads our DataFrame instead of a file
        with patch("pandas.read_csv", return_value=df):
            # Call the function under test (assumed to be available in the test environment)
            X_train, X_valid, y_train, y_valid = prepreprocess()

        # Basic sanity checks
        # Total samples should be preserved
        self.assertEqual(len(X_train) + len(X_valid), n_samples)

        # PassengerId should be dropped from features
        self.assertNotIn("PassengerId", X_train.columns)
        self.assertNotIn("PassengerId", X_valid.columns)

        # Transported should not be a feature column (it's the target)
        self.assertNotIn("Transported", X_train.columns)
        self.assertNotIn("Transported", X_valid.columns)

        # Feature columns count should match (only "Age" remains)
        self.assertEqual(X_train.shape[1], 1)
        self.assertEqual(X_valid.shape[1], 1)

        # Labels should be numeric (LabelEncoder applied) and contain only 0/1
        unique_labels = set(np.unique(y_train).tolist() + np.unique(y_valid).tolist())
        self.assertTrue(unique_labels.issubset({0, 1}))

        # Check expected split sizes (test_size=0.10 -> 1 validation sample for n=10)
        self.assertEqual(len(X_valid), 1)
        self.assertEqual(len(y_valid), 1)
        self.assertEqual(len(X_train), 9)
        self.assertEqual(len(y_train), 9)
