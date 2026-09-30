import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.repomap')
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
        """Ensure RepoMap falls back to os.getcwd() when root is falsy."""
        # Monkeypatch load_tags_cache to avoid touching filesystem/sqlite during init
        orig_load = RepoMap.load_tags_cache

        def _fake_load(self):
            # Simulate a simple in-memory cache to avoid sqlite operations
            self.TAGS_CACHE = {}

        RepoMap.load_tags_cache = _fake_load
        try:
            cwd = os.getcwd()

            class DummyIO:
                def __init__(self):
                    self.messages = []

                def tool_output(self, msg):
                    self.messages.append(("out", msg))

                def tool_warning(self, msg):
                    self.messages.append(("warn", msg))

                def tool_error(self, msg):
                    self.messages.append(("err", msg))

            io = DummyIO()

            # Create RepoMap with a falsy root to trigger root = os.getcwd()
            rm = RepoMap(root=None, io=io)

            # Verify the root was set to current working directory
            self.assertEqual(rm.root, cwd)
        finally:
            RepoMap.load_tags_cache = orig_load
