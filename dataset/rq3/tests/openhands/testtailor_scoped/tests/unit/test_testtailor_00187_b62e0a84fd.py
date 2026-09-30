import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.forgejo.service.features')
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
        """Builds repo API URL using normalized microagents_path (stripped of slashes)."""
        class Dummy(ForgejoFeaturesMixin):
            def _split_repo(self, repository: str):
                # Return fixed owner/repo for testing
                return ("alice", "myrepo")

            def _build_repo_api_url(self, owner: str, repo: str, *parts: str) -> str:
                # Simple predictable URL builder for assertion
                return f"https://forgejo.example/{owner}/{repo}/" + "/".join(parts)

        dummy = Dummy()

        # Use __import__ to obtain asyncio without an import statement at top-level
        asyncio = __import__('asyncio')

        # Case: path with leading and trailing slashes should be normalized
        result = asyncio.run(
            dummy._get_microagents_directory_url("alice/myrepo", "/some/nested/path/")
        )
        self.assertEqual(
            result, "https://forgejo.example/alice/myrepo/contents/some/nested/path"
        )

        # Case: empty path should produce an URL ending with 'contents/'
        result_empty = asyncio.run(
            dummy._get_microagents_directory_url("alice/myrepo", "")
        )
        self.assertEqual(result_empty, "https://forgejo.example/alice/myrepo/contents/")
