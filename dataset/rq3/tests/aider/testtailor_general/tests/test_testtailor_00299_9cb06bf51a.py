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
        """When the cache file contains invalid JSON, _load_cache should set
        self.content to None (triggering the JSONDecodeError branch)."""
        import tempfile
        from pathlib import Path
        from aider.openrouter import OpenRouterModelManager

        # Create a temporary directory to act as HOME/.aider/caches
        tmp = tempfile.TemporaryDirectory()
        tmp_path = Path(tmp.name)

        try:
            cache_dir = tmp_path / ".aider" / "caches"
            cache_dir.mkdir(parents=True)
            cache_file = cache_dir / "openrouter_models.json"

            # Write invalid JSON so json.loads raises JSONDecodeError
            cache_file.write_text("this is not valid json")

            manager = OpenRouterModelManager()
            # Point the manager at our temp cache paths
            manager.cache_dir = cache_dir
            manager.cache_file = cache_file

            # Give content a prior value so we can confirm it gets cleared
            manager.content = {"will": "be_cleared"}

            # Exercise the code under test
            manager._load_cache()

            # The invalid JSON path should set content to None and mark cache loaded
            self.assertIsNone(manager.content)
            self.assertTrue(manager._cache_loaded)
        finally:
            tmp.cleanup()
