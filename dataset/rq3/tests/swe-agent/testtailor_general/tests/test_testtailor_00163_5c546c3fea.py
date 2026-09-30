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
        """Ensure .yaml traj_path triggers yaml.safe_load branch in RunReplay.__init__"""
        from types import SimpleNamespace
        from pathlib import Path
        import tempfile
        import os

        # Capture the traj_data passed into _get_config_from_agent
        captured = []

        # Monkeypatch RunReplay._get_config_from_agent to capture the parsed data
        original_get_config = RunReplay._get_config_from_agent

        def fake_get_config(self, traj_data):
            captured.append(traj_data)
            # Return a minimal config-like object sufficient for __init__
            return SimpleNamespace(env=SimpleNamespace(deployment="unused"), agent=SimpleNamespace(model=SimpleNamespace()))

        RunReplay._get_config_from_agent = fake_get_config

        # Create a temporary YAML file (content is valid YAML but not valid JSON)
        tmp_file = tempfile.NamedTemporaryFile(suffix=".yaml", delete=False)
        try:
            tmp_path = Path(tmp_file.name)
            tmp_file.write(b"replay_config:\n  foo: bar\n")
            tmp_file.flush()
            tmp_file.close()

            # Create a temporary output directory
            out_dir = Path(tempfile.mkdtemp())

            # Instantiate RunReplay with an explicit deployment to avoid get_deployment calls
            rr = RunReplay(
                traj_path=tmp_path,
                deployment=object(),
                output_dir=out_dir,
                _catch_errors=False,
                _require_zero_exit_code=False,
            )

            # Verify that our fake_get_config was called and received a dict parsed by yaml.safe_load
            self.assertTrue(len(captured) == 1, "Expected _get_config_from_agent to be called once")
            traj_data = captured[0]
            self.assertIsInstance(traj_data, dict, "Expected traj_data to be a dict from yaml.safe_load")
            self.assertIn("replay_config", traj_data)
            self.assertEqual(traj_data["replay_config"], {"foo": "bar"})
        finally:
            # Restore the original method and cleanup files/dirs
            RunReplay._get_config_from_agent = original_get_config
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            try:
                # remove output dir
                os.rmdir(out_dir)
            except Exception:
                pass
