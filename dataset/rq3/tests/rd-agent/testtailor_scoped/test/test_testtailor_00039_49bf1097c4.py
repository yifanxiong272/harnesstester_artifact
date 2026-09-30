import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.factor_coder.evaluators')
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
        """Ensure FactorEvaluatorForCoder initializes its sub-evaluators with the provided scen."""
        scen = object()
        evaluator = FactorEvaluatorForCoder(scen=scen)

        # Sub-evaluators should be created
        self.assertIsNotNone(evaluator.value_evaluator)
        self.assertIsNotNone(evaluator.code_evaluator)
        self.assertIsNotNone(evaluator.final_decision_evaluator)

        # They should be instances of the expected classes
        self.assertIsInstance(evaluator.value_evaluator, FactorValueEvaluator)
        self.assertIsInstance(evaluator.code_evaluator, FactorCodeEvaluator)
        self.assertIsInstance(evaluator.final_decision_evaluator, FactorFinalDecisionEvaluator)

        # And each should carry the same scen passed to the parent
        self.assertIs(evaluator.value_evaluator.scen, scen)
        self.assertIs(evaluator.code_evaluator.scen, scen)
        self.assertIs(evaluator.final_decision_evaluator.scen, scen)
