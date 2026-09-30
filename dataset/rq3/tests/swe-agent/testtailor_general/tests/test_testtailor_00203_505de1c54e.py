import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.run_replay')
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
        """Ensure that when deployment is None, RunReplay calls get_deployment with the config env.deployment value."""
        # Create a temporary trajectory file (content doesn't matter because we patch _get_config_from_agent)
        tmp_traj = Path(tempfile.NamedTemporaryFile(suffix=".json", delete=False).name)
        tmp_traj.write_text("{}")

        # Create a temporary output dir
        tmp_output = Path(tempfile.mkdtemp())

        # Prepare a fake config object with the expected structure used in __init__
        fake_config = type("FakeConfig", (), {})()
        fake_env = type("FakeEnv", (), {})()
        fake_env.deployment = "fake-deployment"
        fake_config.env = fake_env

        sentinel = object()
        # Patch get_deployment in the module where RunReplay is defined to return a sentinel
        with patch("sweagent.run.run_replay.get_deployment", return_value=sentinel) as mock_get_deployment:
            # Patch RunReplay._get_config_from_agent to return our fake_config so __init__ proceeds
            with patch.object(RunReplay, "_get_config_from_agent", return_value=fake_config) as mock_get_config:
                rr = RunReplay(traj_path=tmp_traj, deployment=None, output_dir=tmp_output)
                # Ensure our patched methods were called as expected
                mock_get_config.assert_called_once()
                mock_get_deployment.assert_called_once_with("fake-deployment")
                # The instance should have deployment set to the sentinel returned by get_deployment
                self.assertIs(rr.deployment, sentinel)

        # Cleanup
        try:
            tmp_traj.unlink()
        except Exception:
            pass
        try:
            shutil.rmtree(tmp_output)
        except Exception:
            pass
