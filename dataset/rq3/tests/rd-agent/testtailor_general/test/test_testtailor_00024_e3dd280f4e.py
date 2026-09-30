import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.log.ui.qlib_report_figure')
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
        # prepare a DataFrame where is_ex=True path is taken
        idx = pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"])
        df = pd.DataFrame(
            {
                # minimum value is at "2020-01-02" -> end_date
                "cum_ex_return_wo_cost_mdd": [-0.10, -0.25, -0.05],
                # among rows up to end_date (first two), the maximum is at "2020-01-01" -> start_date
                "cum_ex_return_wo_cost": [0.40, 0.20, 0.30],
            },
            index=idx,
        )

        start_date, end_date = _calculate_maximum(df, is_ex=True)

        self.assertEqual(end_date, idx[1])
        self.assertEqual(start_date, idx[0])
