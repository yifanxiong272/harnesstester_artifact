import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.openrouter')
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
        """Ensure get_model_info matches a model id when the provided model route
        includes a suffix after ':' (exercising the branch that splits on ':')."""
        # Prepare payload where the record id matches the route without the ":suffix"
        payload = {
            "data": [
                {
                    "id": "foo/bar",
                    "context_length": 4096,
                    "pricing": {"prompt": "10", "completion": "20"},
                }
            ]
        }

        # Minimal stand-in for requests.Response used by OpenRouterModelManager
        class DummyResponse:
            def __init__(self, json_data):
                self.status_code = 200
                self._json_data = json_data

            def json(self):
                return self._json_data

        # Patch out network and home directory behavior, restore after test
        orig_requests_get = requests.get
        orig_path_home = Path.home
        tmp_dir = None
        try:
            # Create a temporary directory under the current working directory
            tmp_dir = Path.cwd() / f".tmp_openrouter_{int(__import__('time').time() * 1000)}"
            tmp_dir.mkdir(exist_ok=True)

            # Ensure requests.get returns our payload
            requests.get = lambda *a, **k: DummyResponse(payload)
            # Force the cache directory to be inside our temporary home
            Path.home = staticmethod(lambda: tmp_dir)

            manager = OpenRouterModelManager()
            # Provide a model with a ":suffix" so the code will split and consider the
            # id without the suffix when searching the payload.
            info = manager.get_model_info("openrouter/foo/bar:baz")

            self.assertEqual(info["max_input_tokens"], 4096)
            self.assertEqual(info["max_tokens"], 4096)
            self.assertEqual(info["max_output_tokens"], 4096)
            self.assertEqual(info["input_cost_per_token"], 10.0)
            self.assertEqual(info["output_cost_per_token"], 20.0)
            self.assertEqual(info["litellm_provider"], "openrouter")
        finally:
            # Restore patched globals and remove temporary directory
            requests.get = orig_requests_get
            Path.home = orig_path_home
            if tmp_dir and tmp_dir.exists():
                try:
                    __import__("shutil").rmtree(tmp_dir)
                except Exception:
                    pass
