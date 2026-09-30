import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.models')
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
        """Ensure GenericAPIModelConfig with name 'replay' is converted to ReplayModelConfig and returns a ReplayModel."""
        # Create a temporary replay file that ReplayModel will accept
        p = Path.cwd() / "temp_replay_file.traj"
        try:
            # Write a single valid JSON line representing a replay action list
            p.write_text('{"1": [{"message": "submit"}]}\n')

            # Create a temporary GenericAPIModelConfig subclass instance that carries a replay_path
            class TempGeneric(GenericAPIModelConfig):
                # ensure name is 'replay' so get_model will attempt conversion
                name: str = "replay"
                replay_path: Path

            args = TempGeneric(replay_path=p)
            tools = ToolConfig()

            model = get_model(args, tools)

            # Should have been converted and returned as a ReplayModel instance
            self.assertIsInstance(model, ReplayModel)
        finally:
            # Clean up temp file
            if p.exists():
                p.unlink()
