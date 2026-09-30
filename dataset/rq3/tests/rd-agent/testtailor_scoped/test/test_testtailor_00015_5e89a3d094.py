import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.kaggle.developer.feedback')
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
        """Test process_results produces combined dataframe and correct description"""
        # Create instance without running its __init__
        inst = object.__new__(KGExperiment2Feedback)

        # Provide minimal scen with evaluation_metric_direction attribute
        class DummyScen:
            def __init__(self, val):
                self.evaluation_metric_direction = val

        inst.scen = DummyScen(True)

        # Prepare inputs so each DataFrame has exactly one column (so concat yields two columns)
        current_result = {"Metric": [0.8]}
        sota_result = {"Metric": [0.75]}

        combined_df, evaluation_description = inst.process_results(current_result, sota_result)

        # Basic structure checks
        self.assertIsInstance(combined_df, pd.DataFrame)
        self.assertIn("current_df", combined_df.columns)
        self.assertIn("sota_df", combined_df.columns)
        self.assertIn("Note", combined_df.columns)
        self.assertEqual(combined_df.shape[0], 1)

        # Value checks
        self.assertAlmostEqual(float(combined_df["current_df"].iloc[0]), 0.8)
        self.assertAlmostEqual(float(combined_df["sota_df"].iloc[0]), 0.75)

        # Description check for evaluation_direction=True -> 'higher'
        expected_desc = "Direction of improvement (higher/lower is better) should be judged per metric. Here 'higher' is better for the metrics."
        self.assertEqual(evaluation_description, expected_desc)
        self.assertTrue((combined_df["Note"] == expected_desc).all())
