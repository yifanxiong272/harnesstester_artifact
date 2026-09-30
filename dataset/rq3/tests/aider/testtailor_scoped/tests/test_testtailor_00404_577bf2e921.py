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
        """When get_ranked_tags_map raises RecursionError, get_repo_map should disable the map."""
        # Create a mocked IO object with a tool_error method
        mock_io = MagicMock()
        mock_io.tool_error = MagicMock()

        # Patch load_tags_cache so RepoMap.__init__ doesn't try to create a real Cache
        with patch.object(RepoMap, "load_tags_cache", return_value=None):
            repo_map = RepoMap(map_tokens=1024, root=os.getcwd(), io=mock_io)

        # Ensure initial state is enabled
        self.assertGreater(repo_map.max_map_tokens, 0)

        # Make get_ranked_tags_map raise RecursionError to trigger the except branch
        repo_map.get_ranked_tags_map = MagicMock(side_effect=RecursionError)

        # Call get_repo_map with a non-empty other_files so it proceeds to call get_ranked_tags_map
        result = repo_map.get_repo_map(chat_files=["a_file"], other_files=["other_file"])

        # Verify behavior: tool_error called, max_map_tokens disabled and result is None
        mock_io.tool_error.assert_called_once_with("Disabling repo map, git repo too large?")
        self.assertEqual(repo_map.max_map_tokens, 0)
        self.assertIsNone(result)
