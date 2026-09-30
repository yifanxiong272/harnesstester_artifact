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
        """Ensure that when path is None and a .env exists in CWD, the function uses cwd .env."""
        tempfile_mod = __import__("tempfile")
        os = __import__("os")
        pathlib = __import__("pathlib")
        Path = pathlib.Path

        td = tempfile_mod.TemporaryDirectory()
        old_cwd = os.getcwd()
        try:
            os.chdir(td.name)
            env_path = Path(td.name) / ".env"
            env_path.write_text("DUMMY=1\n")

            # Patch the load_dotenv used by the function by injecting into its globals
            globs = load_environment_variables.__globals__
            original_load_dotenv = globs.get("load_dotenv")
            called = []

            def fake_load_dotenv(dotenv_path=None):
                called.append(dotenv_path)
                return True

            globs["load_dotenv"] = fake_load_dotenv

            try:
                # Call with None to trigger the cwd lookup branch
                load_environment_variables(None)
            finally:
                # restore original
                if original_load_dotenv is not None:
                    globs["load_dotenv"] = original_load_dotenv
                else:
                    del globs["load_dotenv"]

            # Assert our fake was called with the .env in CWD
            self.assertTrue(called, "load_dotenv was not called")
            self.assertEqual(Path(called[0]).resolve(), env_path.resolve())
        finally:
            os.chdir(old_cwd)
            td.cleanup()
