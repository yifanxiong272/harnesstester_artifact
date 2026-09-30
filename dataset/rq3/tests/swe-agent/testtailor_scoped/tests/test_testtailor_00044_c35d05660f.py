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
        """Ensure set_default_output_dir falls back to 'unknown_model' when agent.model.id is missing."""
        # Create a RunSingleConfig instance without running pydantic init
        rsc = RunSingleConfig.__new__(RunSingleConfig)
        # Provide the attribute pydantic expects when setting fields
        rsc.__pydantic_fields_set__ = set()

        # Ensure the sentinel default is present so the branch is taken
        rsc.output_dir = Path("DEFAULT")

        # Minimal problem_statement with an id attribute
        class PS:
            id = "test_problem_123"
        rsc.problem_statement = PS()

        # Minimal agent whose model has no 'id' attribute to trigger the AttributeError path
        class Agent:
            pass
        rsc.agent = Agent()
        rsc.agent.model = object()  # plain object has no 'id'

        # Ensure _config_files is not set so getattr falls back to ["no_config"]
        if hasattr(rsc, "_config_files"):
            delattr(rsc, "_config_files")

        # Call the method under test
        rsc.set_default_output_dir()

        # Validate the resulting path
        expected_name = f"no_config__unknown_model___{rsc.problem_statement.id}"
        expected_prefix = Path.cwd() / "trajectories" / getpass.getuser()
        self.assertTrue(str(rsc.output_dir).startswith(str(expected_prefix)))
        self.assertEqual(rsc.output_dir.name, expected_name)
        self.assertIn("unknown_model", rsc.output_dir.name)
