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
        """Ensure cached openrouter models file is read when present and fresh."""
        tempfile = __import__("tempfile")
        json = __import__("json")
        pathlib = __import__("pathlib")
        Path = pathlib.Path

        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)

            # Prepare a valid cached payload in the expected location
            cache_dir = tmp_path / ".aider" / "caches"
            cache_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "data": [
                    {
                        "id": "mistralai/mistral-medium-3",
                        "context_length": 32768,
                        "pricing": {"prompt": "100", "completion": "200"},
                        "top_provider": {"context_length": 32768},
                    }
                ]
            }
            cache_file = cache_dir / "openrouter_models.json"
            cache_file.write_text(json.dumps(payload))

            # Monkeypatch Path.home to point to our temp dir, restoring afterwards.
            orig_home = Path.home
            Path.home = staticmethod(lambda: tmp_path)
            try:
                manager = OpenRouterModelManager()
                info = manager.get_model_info("openrouter/mistralai/mistral-medium-3")

                self.assertEqual(info["max_input_tokens"], 32768)
                self.assertEqual(info["input_cost_per_token"], 100.0)
                self.assertEqual(info["output_cost_per_token"], 200.0)
                self.assertEqual(info["litellm_provider"], "openrouter")
            finally:
                Path.home = orig_home
