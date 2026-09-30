import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.qlib.developer.feedback')
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
        # Prepare values for the three IMPORTANT_METRICS so selection via .loc works
        current_values = {
            "IC": 0.1234567,
            "1day.excess_return_with_cost.annualized_return": 0.1111111,
            "1day.excess_return_with_cost.max_drawdown": -0.2222222,
        }

        sota_values = {
            "IC": 0.2234567,
            "1day.excess_return_with_cost.annualized_return": 0.2111111,
            "1day.excess_return_with_cost.max_drawdown": -0.1222222,
        }

        # Build DataFrames whose single column is named "0" (string) so the rename in
        # process_results matches columns={"0": "Current Result"} / {"0": "SOTA Result"}
        current_df = pd.DataFrame({"0": pd.Series(current_values)})
        sota_df = pd.DataFrame({"0": pd.Series(sota_values)})

        result = process_results(current_df, sota_df)

        metrics = [
            "IC",
            "1day.excess_return_with_cost.annualized_return",
            "1day.excess_return_with_cost.max_drawdown",
        ]

        expected_parts = []
        for m in metrics:
            expected_parts.append(
                f"{m} of Current Result is {current_values[m]:.6f}, of SOTA Result is {sota_values[m]:.6f}"
            )
        expected = "; ".join(expected_parts)

        self.assertEqual(result, expected)
