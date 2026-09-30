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
        """Ensure a GenericAPIModelConfig with name 'replay' is converted to ReplayModelConfig
        and get_model returns a ReplayModel (needs an existing replay file).
        """
        # Create a temporary directory in a way that is robust if tempfile/shutil aren't available
        tmpdir_created_by_tempfile = False
        if "tempfile" in globals():
            tmpdir = Path(tempfile.mkdtemp())
            tmpdir_created_by_tempfile = True
        else:
            # Fallback: create a directory in the current working directory
            tmpdir = Path.cwd() / "tmp_replay_test"
            tmpdir.mkdir(exist_ok=True)

        try:
            replay_file = tmpdir / "test_replay.traj"
            # Write a simple replay trajectory (JSON per-line); ReplayModel expects each line to be JSON
            replay_file.write_text('{"actions": ["submit"]}\n')

            # Create a Generic-like config that has a replay_path field but is still an instance
            # of GenericAPIModelConfig (i.e., not already ReplayModelConfig).
            class FakeGenericWithReplay(GenericAPIModelConfig):
                replay_path: Path

            args = FakeGenericWithReplay(name="replay", replay_path=replay_file)
            tools = ToolConfig()  # default tools are fine for ReplayModel

            model = get_model(args, tools)
            # Should have converted to ReplayModel and returned that instance
            self.assertIsInstance(model, ReplayModel)
            # basic behavior: there is at least one replay loaded
            self.assertTrue(getattr(model, "_replays", []), "Replay actions should be loaded")
        finally:
            # Clean up created files/dirs in a safe way depending on available modules
            try:
                if replay_file.exists():
                    replay_file.unlink()
            except Exception:
                pass
            try:
                if tmpdir_created_by_tempfile:
                    if "shutil" in globals():
                        shutil.rmtree(tmpdir, ignore_errors=True)
                    else:
                        # Attempt to remove directory (should be empty now)
                        tmpdir.rmdir()
                else:
                    # Remove fallback directory if empty
                    tmpdir.rmdir()
            except Exception:
                pass
