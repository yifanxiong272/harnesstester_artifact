import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('multi_agents.main')
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
        """Ensure open_task reads task.json from the module directory and returns the parsed JSON."""
        # Use the same os/json modules that the function under test uses to avoid importing here
        globs = open_task.__globals__
        os_mod = globs['os']
        json_mod = globs['json']

        # Create a unique temporary directory under the current working directory
        tmpdir = os_mod.path.join(os_mod.getcwd(), "tmp_test_" + str(id(object())))
        try:
            os_mod.mkdir(tmpdir)

            # Write task.json into the temporary directory
            expected_task = {"goal": "complete unit test", "model": "base-model"}
            task_json_path = os_mod.path.join(tmpdir, "task.json")
            with open(task_json_path, "w") as f:
                json_mod.dump(expected_task, f)

            # Patch the module __file__ used by open_task so it looks in tmpdir
            original_file = globs.get("__file__", None)
            globs["__file__"] = os_mod.path.join(tmpdir, "fake_module.py")

            # Ensure STRATEGIC_LLM is not set to avoid model override
            original_env = os_mod.environ.pop("STRATEGIC_LLM", None)

            # Call the function under test
            result = open_task()

            # Verify the returned task matches the file contents
            self.assertEqual(result, expected_task)
        finally:
            # Restore environment and module state, clean up tmpdir
            if original_env is not None:
                os_mod.environ["STRATEGIC_LLM"] = original_env
            else:
                if "STRATEGIC_LLM" in os_mod.environ:
                    try:
                        del os_mod.environ["STRATEGIC_LLM"]
                    except Exception:
                        pass

            if original_file is None:
                try:
                    del globs["__file__"]
                except Exception:
                    pass
            else:
                globs["__file__"] = original_file

            # Remove created files and directory if they exist
            try:
                if os_mod.path.exists(task_json_path):
                    os_mod.remove(task_json_path)
            except Exception:
                pass
            try:
                if os_mod.path.exists(tmpdir):
                    os_mod.rmdir(tmpdir)
            except Exception:
                pass
