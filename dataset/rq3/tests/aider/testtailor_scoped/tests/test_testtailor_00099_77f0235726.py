import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.chat_chunks')
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
        """Ensure add_cache_control_headers marks repo messages as cacheable when repo is present."""
        # Create ChatChunks and prepare messages
        chunks = ChatChunks()

        # Ensure examples is empty so the system branch is taken for the first add_cache_control call
        chunks.examples = []
        chunks.system = [{"role": "system", "content": "system prompt"}]

        # Prepare repo so that the `if self.repo:` branch is taken
        chunks.repo = [{"role": "user", "content": "repo map content"}]

        # Ensure other lists exist but remain unaffected
        chunks.readonly_files = []
        chunks.chat_files = []

        # Call the method under test
        chunks.add_cache_control_headers()

        # After calling, system's last message should have been wrapped and marked cacheable
        sys_content = chunks.system[-1]["content"]
        self.assertIsInstance(sys_content, list)
        self.assertIsInstance(sys_content[0], dict)
        self.assertEqual(sys_content[0]["type"], "text")
        self.assertEqual(sys_content[0]["text"], "system prompt")
        self.assertIn("cache_control", sys_content[0])
        self.assertEqual(sys_content[0]["cache_control"]["type"], "ephemeral")

        # Repo's last message should have been wrapped and marked cacheable (target branch)
        repo_content = chunks.repo[-1]["content"]
        self.assertIsInstance(repo_content, list)
        self.assertIsInstance(repo_content[0], dict)
        self.assertEqual(repo_content[0]["type"], "text")
        self.assertEqual(repo_content[0]["text"], "repo map content")
        self.assertIn("cache_control", repo_content[0])
        self.assertEqual(repo_content[0]["cache_control"]["type"], "ephemeral")
