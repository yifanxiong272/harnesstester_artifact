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
        name = "my_model"
        description = "A test model"
        architecture = "CNN"
        hyperparameters = {"lr": "0.01", "optimizer": "adam"}
        training_hyperparameters = {"batch_size": "32", "epochs": "10"}
        formulation = "classification"
        variables = {"input": "image", "target": "label"}
        model_type = "Tabular"

        # instantiate the ModelTask
        task = ModelTask(
            name=name,
            description=description,
            architecture=architecture,
            hyperparameters=hyperparameters,
            training_hyperparameters=training_hyperparameters,
            formulation=formulation,
            variables=variables,
            model_type=model_type,
        )

        # verify attributes were assigned correctly
        self.assertEqual(task.formulation, formulation)
        self.assertEqual(task.architecture, architecture)
        self.assertEqual(task.variables, variables)
        self.assertEqual(task.hyperparameters, hyperparameters)
        self.assertEqual(task.training_hyperparameters, training_hyperparameters)
        self.assertEqual(task.model_type, model_type)

        # verify get_task_information output matches expected formatted string
        expected_info = (
            f"name: {name}\n"
            f"description: {description}\n"
            f"formulation: {formulation}\n"
            f"architecture: {architecture}\n"
            f"variables: {variables}\n"
            f"hyperparameters: {hyperparameters}\n"
            f"training_hyperparameters: {training_hyperparameters}\n"
            f"model_type: {model_type}\n"
        )
        self.assertEqual(task.get_task_information(), expected_info)

        # verify brief information
        expected_brief = (
            f"name: {name}\n"
            f"description: {description}\n"
            f"architecture: {architecture}\n"
            f"hyperparameters: {hyperparameters}\n"
            f"training_hyperparameters: {training_hyperparameters}\n"
            f"model_type: {model_type}\n"
        )
        self.assertEqual(task.get_task_brief_information(), expected_brief)

        # repr and from_dict
        self.assertEqual(repr(task), f"<ModelTask {name}>")
        as_dict = {
            "name": name,
            "description": description,
            "architecture": architecture,
            "hyperparameters": hyperparameters,
            "training_hyperparameters": training_hyperparameters,
            "formulation": formulation,
            "variables": variables,
            "model_type": model_type,
        }
        task_from_dict = ModelTask.from_dict(as_dict)
        self.assertIsInstance(task_from_dict, ModelTask)
        self.assertEqual(task_from_dict.name, name)
        self.assertEqual(task_from_dict.architecture, architecture)
