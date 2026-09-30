import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.qlib.developer.model_runner')
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
        """Trigger the branch where based_experiments exists and last.result is None,
        so that develop calls itself recursively and replaces the last based_experiment.
        """
        # Create a runner instance without calling __init__ to avoid required args
        runner = object.__new__(QlibModelRunner)
        # Bind the original (undecorated) develop method to the instance so recursive calls
        # inside develop use the undecorated implementation as well.
        runner.develop = QlibModelRunner.develop.__wrapped__.__get__(runner, QlibModelRunner)

        # Dummy workspace that provides inject_files and execute used in develop
        class DummyWorkspace:
            def __init__(self, exec_result):
                self.exec_result = exec_result
                self.injected = None
                # workspace_path is only used when SOTA factors exist; we won't trigger that branch.
                self.workspace_path = None
            def inject_files(self, **kwargs):
                self.injected = kwargs
            def execute(self, qlib_config_name=None, run_env=None):
                # Return a non-None result to avoid ModelEmptyError
                return (self.exec_result, f"stdout-{qlib_config_name}")

        # Minimal experiment-like object
        class DummyExp:
            pass

        # Build inner (based) experiment whose result is None so runner.develop should recurse into it
        inner = DummyExp()
        inner.result = None
        inner.based_experiments = []  # no further recursion
        inner.sub_workspace_list = [DummyExp()]
        inner.sub_workspace_list[0].file_dict = {"model.py": "print('inner')"}
        inner.experiment_workspace = DummyWorkspace("inner_result")
        inner.sub_tasks = [DummyExp()]
        inner.sub_tasks[0].training_hyperparameters = None
        inner.sub_tasks[0].name = "inner_task"
        inner.sub_tasks[0].model_type = "Tabular"
        inner.stdout = ""

        # Build outer experiment which has the inner as a based_experiment
        outer = DummyExp()
        outer.based_experiments = [inner]
        outer.sub_workspace_list = [DummyExp()]
        outer.sub_workspace_list[0].file_dict = {"model.py": "print('outer')"}
        outer.experiment_workspace = DummyWorkspace("outer_result")
        outer.sub_tasks = [DummyExp()]
        outer.sub_tasks[0].training_hyperparameters = None
        outer.sub_tasks[0].name = "outer_task"
        outer.sub_tasks[0].model_type = "Tabular"
        outer.stdout = ""

        # Call the bound (undecorated) develop to avoid any caching wrapper side-effects
        developed = runner.develop(outer)

        # After develop, the inner based_experiment should have been replaced/developed with a result
        self.assertIsNotNone(developed.based_experiments[-1].result)
        self.assertEqual(developed.based_experiments[-1].result, "inner_result")
        # Outer experiment should also have its result set from its workspace.execute
        self.assertEqual(developed.result, "outer_result")
        # Ensure inject_files was called on the outer workspace (sanity check)
        self.assertIn("model.py", developed.experiment_workspace.injected)
