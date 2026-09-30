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
        """Ensure add_cache_control_headers marks repo branch and related parts when repo is present."""
        chunks = ChatChunks()

        # examples empty so system should be used for the first cache_control
        chunks.system.append({"role": "system", "content": "system content"})

        # repo present -> should trigger the branch that calls add_cache_control(self.repo)
        # use a dict content to exercise the branch where content is already a dict
        chunks.repo.append({"role": "system", "content": {"type": "text", "text": "repo content"}})

        # readonly_files present but should NOT be individually modified when repo exists
        chunks.readonly_files.append({"role": "system", "content": "readonly content"})

        # chat_files always gets cache_control applied
        chunks.chat_files.append({"role": "assistant", "content": "chat content"})

        # Call the method under test
        chunks.add_cache_control_headers()

        # repo should have content converted to a list and contain cache_control
        repo_content = chunks.repo[-1]["content"]
        self.assertIsInstance(repo_content, list)
        self.assertIn("cache_control", repo_content[0])
        self.assertEqual(repo_content[0]["cache_control"]["type"], "ephemeral")

        # system should have been cached because examples was empty
        system_content = chunks.system[-1]["content"]
        self.assertIsInstance(system_content, list)
        self.assertIn("cache_control", system_content[0])
        self.assertEqual(system_content[0]["cache_control"]["type"], "ephemeral")

        # chat_files should also be cached
        chat_content = chunks.chat_files[-1]["content"]
        self.assertIsInstance(chat_content, list)
        self.assertIn("cache_control", chat_content[0])
        self.assertEqual(chat_content[0]["cache_control"]["type"], "ephemeral")

        # readonly_files should remain unchanged (not converted to list) because repo branch was taken
        readonly_content = chunks.readonly_files[-1]["content"]
        self.assertIsInstance(readonly_content, str)
        self.assertEqual(readonly_content, "readonly content")
