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
        """Ensure update_config merging preserves existing agent.model when not provided in the update file."""
        # Prepare a temporary YAML update file that *does not* include agent.model
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".yaml", mode="w")
        try:
            tf.write(yaml.safe_dump({"agent": {"other_setting": "value"}}))
            tf.flush()
            tf_path = Path(tf.name)
        finally:
            tf.close()

        # Prepare a fake trajectory replay_config dict that will be validated by the patched model_validate
        initial_replay_config = {
            "agent": {
                "model": {"name": "original_model", "id": "m1", "per_instance_cost_limit": 0.0}
            },
            "env": {},
            "problem_statement": {},
            "output_dir": str(Path("DEFAULT")),
            "actions": {},
        }

        # We'll capture calls to model_validate to inspect the merged dict later
        calls = []

        class FakeAgentModel:
            def __init__(self, model_dict):
                self._model_dict = model_dict

            def model_dump(self, mode="json"):
                return self._model_dict

        class FakeConfig:
            def __init__(self, data):
                # store the raw dict
                self._data = data
                # ensure agent.model is accessible as an object with model_dump
                model_dict = data.get("agent", {}).get("model", {"name": "unknown"})
                # simple holder object to avoid extra imports like SimpleNamespace
                class AgentHolder:
                    pass

                agent_holder = AgentHolder()
                agent_holder.model = FakeAgentModel(model_dict)
                self.agent = agent_holder

            def model_dump(self, mode="json"):
                return self._data

        def fake_model_validate(data):
            # record the incoming dict for assertions and return a FakeConfig built from it
            calls.append(data)
            return FakeConfig(data)

        # Create a RunReplay-like instance without running __init__ (so we can control attributes)
        rr = object.__new__(RunReplay)
        rr._update_config = [tf_path]
        rr._replay_action_trajs_path = Path(tempfile.NamedTemporaryFile(suffix=".json").name)

        # Patch RunSingleConfig.model_validate used inside _get_config_from_agent
        patch_target = "sweagent.run.run_replay.RunSingleConfig.model_validate"
        with unittest.mock.patch(patch_target, side_effect=fake_model_validate):
            # Call the method under test with traj_data containing our initial replay_config
            result_config = RunReplay._get_config_from_agent(rr, {"replay_config": initial_replay_config})

        # Ensure model_validate was called at least twice: initial validate and after merging
        assert len(calls) >= 2

        # The second call input should include agent.model because update_data did not provide it
        merged_input = calls[1]
        assert "agent" in merged_input
        assert "model" in merged_input["agent"], "agent.model should be preserved and inserted into merged dict"

        # The resulting config's agent.model should have been replaced with a ReplayModelConfig
        assert isinstance(result_config.agent.model, ReplayModelConfig)
        assert result_config.agent.model.replay_path == rr._replay_action_trajs_path

        # Clean up temp file
        try:
            tf_path.unlink(missing_ok=True)
        except Exception:
            pass
