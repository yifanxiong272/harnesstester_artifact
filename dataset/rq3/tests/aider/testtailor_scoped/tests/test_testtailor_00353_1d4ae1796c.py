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
        """RepoMap __init__ should call io.tool_output when verbose=True"""
        # Prepare a mock io with a tool_output method
        io = unittest.mock.Mock()
        io.tool_output = unittest.mock.Mock()

        # Patch RepoMap.load_tags_cache to avoid filesystem/cache side effects
        with unittest.mock.patch.object(RepoMap, "load_tags_cache", autospec=True) as mock_load:
            def fake_load(self):
                # ensure TAGS_CACHE exists to avoid later attribute errors
                self.TAGS_CACHE = {}
            mock_load.side_effect = fake_load

            # Instantiate RepoMap with verbose True and a custom map_mul_no_files value
            rm = RepoMap(map_mul_no_files=123, io=io, verbose=True, main_model=None)

        # Verify tool_output was called with the expected initialization message
        io.tool_output.assert_called_once_with(
            "RepoMap initialized with map_mul_no_files: 123"
        )
