import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.kaggle.experiment.templates.covid19-global-forecasting-week-1.fea_share_preprocess')
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
        """Test prepreprocess with small synthetic train/test CSVs."""
        # Prepare synthetic train and test DataFrames
        train_df = pd.DataFrame({
            "Date": ["2020-01-01", "2020-01-02"],
            "Country/Region": ["A", "B"],
            "Province/State": [None, "X"],
            "ConfirmedCases": [10, 20],
            "Fatalities": [1, 2],
            # note: do not include ForecastId for train (will be NaN after concat)
        })

        test_df = pd.DataFrame({
            "Date": ["2020-01-03"],
            "Country/Region": ["A"],
            "Province/State": [None],
            "ForecastId": [100]  # this identifies the test rows after concat
            # test does not need ConfirmedCases/Fatalities
        })

        # Patch pandas.read_csv to return our synthetic DataFrames in order
        with unittest.mock.patch("pandas.read_csv", side_effect=[train_df, test_df]):
            X_train, X_valid, y_train, y_valid, test_features, test_forecastids = prepreprocess()

        # Basic shape checks
        # Original train had 2 rows -> after train_test_split with test_size=0.2 and random_state=42,
        # we expect one row in train and one in valid (n_samples small => one in each)
        self.assertEqual(len(X_train) + len(X_valid), 2)
        self.assertEqual(len(y_train) + len(y_valid), 2)

        # Check feature columns present
        expected_features = ["Country/Region", "Province/State", "Day", "Month", "Year"]
        self.assertListEqual(list(X_train.columns), expected_features)
        self.assertListEqual(list(test_features.columns), expected_features)

        # Check that test ForecastId was preserved (might be float due to NaNs from concat)
        self.assertEqual(len(test_forecastids), 1)
        self.assertIn(int(test_forecastids.iloc[0]), (100,))  # allow 100 or 100.0

        # Validate encoded categorical values and date-derived features for the single test row
        # LabelEncoder will assign 'A'->0, 'B'->1 for Country/Region and 'None'->0, 'X'->1 for Province/State
        row = test_features.iloc[0].tolist()
        self.assertEqual(row[0], 0)      # Country/Region 'A' encoded to 0
        self.assertEqual(row[1], 0)      # Province/State None -> 'None' encoded to 0
        self.assertEqual(row[2], 3)      # Day
        self.assertEqual(row[3], 1)      # Month
        self.assertEqual(row[4], 2020)   # Year

        # Check that targets correspond to the original train values (ConfirmedCases and Fatalities)
        # Combine y_train and y_valid to compare as unordered set of rows
        combined_y = pd.concat([y_train, y_valid]).sort_index()
        # Original train_df had ConfirmedCases [10,20] and Fatalities [1,2]
        self.assertCountEqual(list(combined_y["ConfirmedCases"]), [10, 20])
        self.assertCountEqual(list(combined_y["Fatalities"]), [1, 2])
