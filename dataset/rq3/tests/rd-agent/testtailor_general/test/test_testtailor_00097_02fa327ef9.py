import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.model_coder.model')
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
        # Prepare inputs
        hyperparameters = {"learning_rate": "0.01", "batch_size": "32"}
        training_hyperparameters = {"epochs": "5", "shuffle": "True"}
        formulation = "classification"
        variables = {"input": "float", "label": "int"}
        model_type = "Tabular"

        # Instantiate ModelTask (hyperparameters and training_hyperparameters must be passed as keywords)
        task = ModelTask(
            name="my_model",
            description="a test model task",
            architecture="CNN",
            hyperparameters=hyperparameters,
            training_hyperparameters=training_hyperparameters,
            formulation=formulation,
            variables=variables,
            model_type=model_type,
        )

        # Check that attributes are set as provided
        self.assertEqual(task.name, "my_model")
        self.assertEqual(task.description, "a test model task")
        self.assertEqual(task.architecture, "CNN")
        self.assertEqual(task.formulation, formulation)
        self.assertEqual(task.variables, variables)
        self.assertEqual(task.hyperparameters, hyperparameters)
        self.assertEqual(task.training_hyperparameters, training_hyperparameters)
        self.assertEqual(task.model_type, model_type)

        # get_task_information should include all provided fields
        info = task.get_task_information()
        self.assertIn("name: my_model", info)
        self.assertIn("description: a test model task", info)
        self.assertIn("formulation: classification", info)
        self.assertIn("architecture: CNN", info)
        self.assertIn("variables: {'input': 'float', 'label': 'int'}", info)
        self.assertIn("hyperparameters: {'learning_rate': '0.01', 'batch_size': '32'}", info)
        self.assertIn("training_hyperparameters: {'epochs': '5', 'shuffle': 'True'}", info)
        self.assertIn("model_type: Tabular", info)

        # get_task_brief_information should include the brief fields
        brief = task.get_task_brief_information()
        self.assertIn("name: my_model", brief)
        self.assertIn("description: a test model task", brief)
        self.assertIn("architecture: CNN", brief)
        self.assertIn("hyperparameters: {'learning_rate': '0.01', 'batch_size': '32'}", brief)
        self.assertIn("training_hyperparameters: {'epochs': '5', 'shuffle': 'True'}", brief)
        self.assertIn("model_type: Tabular", brief)

        # repr should follow the pattern <ModelTask name>
        self.assertEqual(repr(task), "<ModelTask my_model>")

        # Test from_dict staticmethod produces an equivalent object
        d = {
            "name": "dict_model",
            "description": "created from dict",
            "architecture": "RNN",
            "hyperparameters": {"lr": "0.001"},
            "training_hyperparameters": {"epochs": "3"},
            "formulation": None,
            "variables": None,
            "model_type": "TimesSeries",
        }
        task_from_dict = ModelTask.from_dict(d)
        self.assertIsInstance(task_from_dict, ModelTask)
        self.assertEqual(task_from_dict.name, "dict_model")
        self.assertEqual(task_from_dict.description, "created from dict")
        self.assertEqual(task_from_dict.architecture, "RNN")
        self.assertEqual(task_from_dict.hyperparameters, {"lr": "0.001"})
        self.assertEqual(task_from_dict.training_hyperparameters, {"epochs": "3"})
        self.assertEqual(task_from_dict.model_type, "TimesSeries")
