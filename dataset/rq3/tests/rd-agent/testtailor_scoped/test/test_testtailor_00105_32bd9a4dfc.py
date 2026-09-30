import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.shared.get_runtime_info')
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
        """Test that get_runtime_environment_by_env uses FBWorkspace.execute and returns stdout from env.run."""
        # Create a dummy Env that returns an object with get_truncated_stdout()
        class DummyEnv(Env):
            def __init__(self):
                from types import SimpleNamespace
                super().__init__(conf=SimpleNamespace())  # conf won't be used since we override run

            def run(self, entry, local_path, env=None, **kwargs):
                class DummyResult:
                    def get_truncated_stdout(self_inner):
                        return "dummy-stdout"
                return DummyResult()

        dummy_env = DummyEnv()

        # Patch Path.read_text so the code doesn't depend on an actual runtime_info.py file on disk.
        with unittest.mock.patch.object(Path, "read_text", return_value="print('hello')"):
            stdout = get_runtime_environment_by_env(dummy_env)

        self.assertEqual(stdout, "dummy-stdout")
