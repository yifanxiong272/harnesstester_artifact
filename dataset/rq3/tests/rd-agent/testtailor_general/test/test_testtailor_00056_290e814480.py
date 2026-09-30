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
        """Test process_results builds combined dataframe and evaluation description"""
        # Local imports (allowed inside test body)
        import sys
        import inspect
        import types
        import pandas as pd

        # Find the KGExperiment2Feedback class in loaded modules
        KGCls = None
        for mod in list(sys.modules.values()):
            if not mod:
                continue
            try:
                candidate = getattr(mod, "KGExperiment2Feedback", None)
                if inspect.isclass(candidate):
                    KGCls = candidate
                    break
            except Exception:
                continue

        self.assertIsNotNone(KGCls, "KGExperiment2Feedback class not found in loaded modules")

        # Prepare a fake self with scen.evaluation_metric_direction attribute
        fake_scen = types.SimpleNamespace(evaluation_metric_direction=True)
        fake_self = types.SimpleNamespace(scen=fake_scen)

        # Prepare current_result and sota_result as pandas Series so pd.DataFrame(...) yields single-column DataFrames
        current_result = pd.Series({"accuracy": 0.80, "loss": 0.20})
        sota_result = pd.Series({"accuracy": 0.85, "loss": 0.25})

        # Call the unbound method with our fake self
        combined_df, evaluation_description = KGCls.process_results(fake_self, current_result, sota_result)

        # Assertions about return types
        self.assertIsInstance(combined_df, pd.DataFrame)
        self.assertIsInstance(evaluation_description, str)

        # The combined dataframe should have two named columns plus the Note column
        self.assertListEqual(list(combined_df.columns), ["current_df", "sota_df", "Note"])

        # The index should contain our metric names and values should match the input series
        self.assertIn("accuracy", combined_df.index)
        self.assertIn("loss", combined_df.index)
        self.assertAlmostEqual(float(combined_df.at["accuracy", "current_df"]), 0.80)
        self.assertAlmostEqual(float(combined_df.at["accuracy", "sota_df"]), 0.85)
        self.assertAlmostEqual(float(combined_df.at["loss", "current_df"]), 0.20)
        self.assertAlmostEqual(float(combined_df.at["loss", "sota_df"]), 0.25)

        # The Note column should contain the evaluation description for every row
        self.assertTrue((combined_df["Note"] == evaluation_description).all())

        # Since we set evaluation_metric_direction=True, the description should mention 'higher'
        self.assertIn("higher", evaluation_description)
