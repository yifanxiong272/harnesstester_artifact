import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.run_single')
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
        """Ensure that when a Path is provided in _config_files, the stem is used."""
        # Create a RunSingleConfig instance without running validation/complex init
        try:
            # pydantic v2
            rsc = RunSingleConfig.model_construct()
        except AttributeError:
            # pydantic v1
            rsc = RunSingleConfig.construct()

        # Ensure the sentinel value triggers the branch
        rsc.output_dir = Path("DEFAULT")

        # Provide simple dummy objects for fields accessed by set_default_output_dir
        class DummyProblem:
            id = "problem_123"

        class DummyModel:
            id = "model_abc"

        class DummyAgent:
            model = DummyModel()

        rsc.problem_statement = DummyProblem()
        rsc.agent = DummyAgent()

        # Make the first config file a Path so isinstance(config_file, Path) is True
        cfg_path = Path("my_config.yaml")
        rsc._config_files = [cfg_path]

        # Call the method under test
        rsc.set_default_output_dir()

        # The output_dir's final path component should use the stem of the config file
        expected_final = f"{cfg_path.stem}__{rsc.agent.model.id}___{rsc.problem_statement.id}"
        self.assertEqual(rsc.output_dir.name, expected_final)

        # It should be nested under a 'trajectories' directory created from cwd
        parent_names = [p.name for p in rsc.output_dir.parents]
        self.assertIn("trajectories", parent_names)

        # And the path should start with the current working directory
        self.assertTrue(str(rsc.output_dir).startswith(str(Path.cwd())))
