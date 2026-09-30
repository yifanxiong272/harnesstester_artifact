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
        """Test process_results with DataFrame inputs having a string "0" column so renaming works
        and formatted values match {:.6f} rounding behavior."""
        # Prepare inputs as DataFrames with a single column named "0" (string),
        # so the function's rename(columns={"0": ...}) call succeeds.
        current_result = pd.DataFrame(
            {
                "0": pd.Series(
                    {
                        "IC": 0.123456789,
                        "1day.excess_return_with_cost.annualized_return": 0.2222222,
                        "1day.excess_return_with_cost.max_drawdown": -0.3333333,
                    }
                )
            }
        )
        sota_result = pd.DataFrame(
            {
                "0": pd.Series(
                    {
                        "IC": 0.0012345,
                        "1day.excess_return_with_cost.annualized_return": -0.1111111,
                        "1day.excess_return_with_cost.max_drawdown": 0.4444444,
                    }
                )
            }
        )

        output = process_results(current_result, sota_result)

        expected = (
            "IC of Current Result is 0.123457, of SOTA Result is 0.001234; "
            "1day.excess_return_with_cost.annualized_return of Current Result is 0.222222, of SOTA Result is -0.111111; "
            "1day.excess_return_with_cost.max_drawdown of Current Result is -0.333333, of SOTA Result is 0.444444"
        )

        self.assertEqual(output, expected)
