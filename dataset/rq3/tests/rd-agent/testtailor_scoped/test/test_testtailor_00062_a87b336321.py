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
        """Test the is_ex=True branch where end_date is idxmin of cum_ex_return_wo_cost_mdd
        and start_date is idxmax of cum_ex_return_wo_cost among indices <= end_date.
        """
        # create a simple DataFrame with integer index
        idx = [0, 1, 2, 3, 4]
        df = pd.DataFrame({
            "cum_ex_return_wo_cost_mdd": [5, 3, -1, 0, 2],  # minimum at index 2
            "cum_ex_return_wo_cost":    [1, 4,  2, 3, 0]   # among indices <=2, max at index 1
        }, index=idx)

        start, end = _calculate_maximum(df, is_ex=True)
        self.assertEqual(start, 1)
        self.assertEqual(end, 2)
