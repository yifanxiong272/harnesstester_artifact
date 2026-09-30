import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.utils.config')
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
        """Ensure that when no path is provided and there's no .env in CWD
        but there is one at REPO_ROOT, load_environment_variables loads it.
        """
        orig_cwd = Path.cwd()
        # create a unique temporary directory under the current working directory
        tmp_cwd = orig_cwd / f"tmp_test_env_cwd_{os.getpid()}"
        # ensure a clean start
        if tmp_cwd.exists():
            try:
                shutil.rmtree(tmp_cwd)
            except Exception:
                pass
        tmp_cwd.mkdir()

        env_path = REPO_ROOT / ".env"
        had_env = env_path.exists()
        backup_path = None

        # If an existing .env was present at REPO_ROOT, back it up to restore later.
        if had_env:
            backup_path = REPO_ROOT / f".env.backup_for_test_{os.getpid()}"
            env_path.rename(backup_path)

        try:
            # switch to a cwd that does NOT contain a .env
            os.chdir(tmp_cwd)
            assert not (tmp_cwd / ".env").exists()

            # create a .env at the repository root
            env_path.write_text("TEST_ENV_VAR_FOR_LOAD=loaded_value\n")

            # ensure the env var is not already set
            os.environ.pop("TEST_ENV_VAR_FOR_LOAD", None)

            # call the function with path=None to trigger the REPO_ROOT branch
            load_environment_variables(None)

            # verify that the variable from REPO_ROOT/.env was loaded into the environment
            self.assertEqual(os.environ.get("TEST_ENV_VAR_FOR_LOAD"), "loaded_value")
        finally:
            # cleanup: remove the test .env we created
            try:
                if env_path.exists():
                    env_path.unlink()
            except Exception:
                pass

            # restore original .env at REPO_ROOT if one existed
            if had_env and backup_path and backup_path.exists():
                backup_path.rename(env_path)

            # restore working directory and remove temporary cwd
            os.chdir(orig_cwd)
            try:
                if tmp_cwd.exists():
                    shutil.rmtree(tmp_cwd)
            except Exception:
                pass
