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
        """Ensure set_default_output_dir uses Path.stem when a config file Path is provided."""
        # Create an instance without running pydantic init and make sure pydantic internals exist
        rsc = object.__new__(RunSingleConfig)
        # pydantic expects this attribute when setting fields on a model instance
        rsc.__pydantic_fields_set__ = set()

        # Set output_dir to the sentinel value to trigger the branch
        rsc.output_dir = Path("DEFAULT")

        # Minimal stubs for problem_statement and agent.model with required 'id' attributes
        rsc.problem_statement = type("PS", (), {"id": "problem1"})()
        model_stub = type("M", (), {"id": "model123"})()
        rsc.agent = type("A", (), {"model": model_stub})()

        # Provide a Path config file so isinstance(config_file, Path) is True
        rsc._config_files = [Path("my_config.yaml")]

        # Call the method under test
        RunSingleConfig.set_default_output_dir(rsc)

        # Expect the stem of the config file (my_config) to be used, not the full filename
        expected = Path.cwd() / "trajectories" / getpass.getuser() / "my_config__model123___problem1"
        self.assertEqual(rsc.output_dir, expected)
