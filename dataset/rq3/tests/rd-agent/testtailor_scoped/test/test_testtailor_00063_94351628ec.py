import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.model_coder.evaluators')
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
        """Ensure evaluate calls target_task.get_task_information and proceeds through evaluation pipeline."""
        # Prepare a ModelTask
        task = ModelTask(
            name="t1",
            description="desc",
            architecture="arch",
            hyperparameters={},
            training_hyperparameters={},
        )

        # Create evaluator with no scenario (scen=None)
        evaluator = ModelCoSTEEREvaluator(scen=None)

        # Create a lightweight subclass of ModelFBWorkspace that allows setting all_codes
        class DummyModelFBWorkspace(ModelFBWorkspace):
            def __init__(self):
                # Avoid heavy initialization in parent
                self.target_task = None

            def execute(
                self,
                batch_size: int = 8,
                num_features: int = 10,
                num_timesteps: int = 4,
                input_value: float = 1.0,
                param_init_value: float = 1.0,
            ):
                import numpy as np

                # Return execution feedback and a numpy array of shape (batch_size, 1)
                return "exec ok", np.zeros((batch_size, 1))

            @property
            def all_codes(self):
                return getattr(self, "_all_codes", "")

            @all_codes.setter
            def all_codes(self, v):
                self._all_codes = v

        impl = DummyModelFBWorkspace()
        impl.all_codes = "print('hello')"

        # Monkeypatch ModelCodeEvaluator.evaluate and ModelFinalEvaluator.evaluate to avoid external API calls
        orig_code_eval = ModelCodeEvaluator.evaluate
        orig_final_eval = ModelFinalEvaluator.evaluate
        try:
            def fake_code_eval(self, target_task, implementation, gt_implementation, model_execution_feedback="", model_value_feedback=""):
                return "code_fb", None

            def fake_final_eval(self, target_task, implementation, gt_implementation, model_execution_feedback, model_shape_feedback, model_value_feedback, model_code_feedback):
                return "final_fb", True

            ModelCodeEvaluator.evaluate = fake_code_eval
            ModelFinalEvaluator.evaluate = fake_final_eval

            # Call evaluate with no ground-truth implementation and no queried_knowledge
            feedback = evaluator.evaluate(target_task=task, implementation=impl, gt_implementation=None, queried_knowledge=None)

            # Assertions: ensure get_task_information was used (no exception) and outputs propagated
            self.assertEqual(feedback.execution_feedback, "exec ok")
            self.assertEqual(feedback.shape_feedback, "The shape of the output is correct.")
            self.assertIn("no ground truth", feedback.value_feedback.lower())
            self.assertEqual(feedback.code_feedback, "code_fb")
            self.assertEqual(feedback.final_feedback, "final_fb")
            self.assertTrue(feedback.final_decision)
            self.assertTrue(feedback.value_generated_flag)
            self.assertFalse(feedback.final_decision_based_on_gt)
        finally:
            # restore original methods
            ModelCodeEvaluator.evaluate = orig_code_eval
            ModelFinalEvaluator.evaluate = orig_final_eval
