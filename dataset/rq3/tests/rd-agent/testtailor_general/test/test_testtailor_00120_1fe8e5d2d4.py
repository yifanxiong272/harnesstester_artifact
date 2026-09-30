import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.qlib.proposal.bandit')
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
        """Test extract_metrics_from_experiment for normal path (try) and exception path (except)"""

        # Helper minimal experiment object with a .result attribute (normal case)
        class ExpGood:
            def __init__(self, result):
                self.result = result

        # Helper experiment where accessing .result raises to trigger the except branch
        class ExpBad:
            @property
            def result(self):
                raise RuntimeError("simulated access error")

        # Normal case: negative max drawdown (common representation), so -mdd becomes positive
        result_good = {
            "IC": 0.1,
            "ICIR": 0.05,
            "Rank IC": 0.02,
            "Rank ICIR": 0.01,
            "1day.excess_return_with_cost.annualized_return ": 0.12,
            "1day.excess_return_with_cost.information_ratio": 0.6,
            "1day.excess_return_with_cost.max_drawdown": -0.25,
        }
        exp_good = ExpGood(result_good)
        metrics_good = extract_metrics_from_experiment(exp_good)

        # Validate fields extracted correctly
        self.assertAlmostEqual(metrics_good.ic, 0.1)
        self.assertAlmostEqual(metrics_good.icir, 0.05)
        self.assertAlmostEqual(metrics_good.rank_ic, 0.02)
        self.assertAlmostEqual(metrics_good.rank_icir, 0.01)
        self.assertAlmostEqual(metrics_good.arr, 0.12)
        self.assertAlmostEqual(metrics_good.ir, 0.6)
        self.assertAlmostEqual(metrics_good.mdd, -0.25)
        # sharpe = arr / -mdd -> 0.12 / 0.25 = 0.48
        self.assertAlmostEqual(metrics_good.sharpe, 0.12 / 0.25)

        # Validate as_vector ordering and -mdd behavior
        vec_good = metrics_good.as_vector().tolist()
        expected_good = [
            0.1,
            0.05,
            0.02,
            0.01,
            0.12,
            0.6,
            0.25,  # -mdd
            0.12 / 0.25,
        ]
        for got, exp in zip(vec_good, expected_good):
            self.assertAlmostEqual(got, exp)

        # Exception case: accessing .result raises -> except branch should return default Metrics()
        exp_bad = ExpBad()
        metrics_bad = extract_metrics_from_experiment(exp_bad)

        # Metrics() defaults all fields to 0.0 per class definition
        self.assertAlmostEqual(metrics_bad.ic, 0.0)
        self.assertAlmostEqual(metrics_bad.icir, 0.0)
        self.assertAlmostEqual(metrics_bad.rank_ic, 0.0)
        self.assertAlmostEqual(metrics_bad.rank_icir, 0.0)
        self.assertAlmostEqual(metrics_bad.arr, 0.0)
        self.assertAlmostEqual(metrics_bad.ir, 0.0)
        self.assertAlmostEqual(metrics_bad.mdd, 0.0)
        self.assertAlmostEqual(metrics_bad.sharpe, 0.0)

        # as_vector should reflect the default values (note -mdd of 0.0 is still 0.0)
        vec_bad = metrics_bad.as_vector().tolist()
        expected_bad = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -0.0, 0.0]
        for got, exp in zip(vec_bad, expected_bad):
            # allow -0.0/0.0 equivalence
            self.assertAlmostEqual(got, exp)
