import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.qlib.developer.factor_runner')
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
        """Ensure calculate_information_coefficient creates a Series with correct length and values."""
        # Construct a DataFrame with 2 SOTA columns and 3 new columns (total 5 columns) and multiple rows
        data = [
            [1, 2, 3, 4, 5],
            [2, 3, 4, 5, 6],
            [3, 4, 5, 6, 7],
            [4, 5, 6, 7, 8],
            [5, 6, 7, 8, 9],
        ]
        concat_feature = pd.DataFrame(data)

        SOTA_feature_column_size = 2
        new_feature_columns_size = 3

        # Call the method as an unbound function (self is not used in the implementation)
        res = QlibFactorRunner.calculate_information_coefficient(None, concat_feature, SOTA_feature_column_size, new_feature_columns_size)

        # The result should be a pandas Series with length equal to product of the sizes
        expected_length = SOTA_feature_column_size * new_feature_columns_size
        self.assertIsInstance(res, pd.Series)
        self.assertEqual(len(res), expected_length)
        self.assertEqual(list(res.index), list(range(expected_length)))

        # Compute expected correlation values and compare (allow NaN equality)
        expected_values = []
        for col1 in range(SOTA_feature_column_size):
            for col2 in range(SOTA_feature_column_size, SOTA_feature_column_size + new_feature_columns_size):
                expected_values.append(concat_feature.iloc[:, col1].corr(concat_feature.iloc[:, col2]))

        for got, exp in zip(res.tolist(), expected_values):
            if pd.isna(exp):
                self.assertTrue(pd.isna(got))
            else:
                # numerical compare
                self.assertAlmostEqual(got, exp, places=12)
