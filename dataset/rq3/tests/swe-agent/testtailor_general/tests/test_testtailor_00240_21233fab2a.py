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
        # Create a minimal RunReplay instance without invoking its __init__
        rr = object.__new__(RunReplay)
        rr._update_config = []
        rr._replay_action_trajs_path = Path(tempfile.NamedTemporaryFile(suffix=".json").name)

        # Prepare traj_data where replay_config is a JSON string (this should trigger json.loads)
        payload = {"agent": {"model": {"name": "orig_model"}}}
        traj_data = {"replay_config": json.dumps(payload)}

        # Create simple fake config objects to be returned by model_validate
        class FakeModel:
            def model_dump(self, mode="json"):
                return {"name": "orig_model"}

        class FakeAgent:
            def __init__(self):
                self.model = FakeModel()

        class FakeConfig:
            def __init__(self):
                self.agent = FakeAgent()

        fake_config = FakeConfig()

        # Patch RunSingleConfig.model_validate to return our fake_config to avoid heavy validation
        with patch.object(RunSingleConfig, "model_validate", return_value=fake_config) as mock_validate:
            config = RunReplay._get_config_from_agent(rr, traj_data)
            mock_validate.assert_called_once()

        # Ensure the string was parsed into a dict
        self.assertIsInstance(traj_data["replay_config"], dict)

        # After running, the returned config.agent.model should be replaced with ReplayModelConfig
        self.assertIsInstance(config.agent.model, ReplayModelConfig)
        self.assertEqual(config.agent.model.replay_path, rr._replay_action_trajs_path)
