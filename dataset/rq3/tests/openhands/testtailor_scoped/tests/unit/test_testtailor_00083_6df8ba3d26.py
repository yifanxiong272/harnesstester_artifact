import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.app_server.utils.llm_metadata')
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
        """Verify get_llm_metadata includes openhands version, WEB_HOST, session_id and user id."""
        # Arrange
        old_web_host = os.environ.get("WEB_HOST")
        os.environ["WEB_HOST"] = "test.host.example"
        try:
            model_name = "gpt-test-model"
            llm_type = "agent"
            conv_str = "conversation-123"
            user_id = "user-42"

            # Act
            metadata = get_llm_metadata(
                model_name, llm_type, conversation_id=conv_str, user_id=user_id
            )

            # Assert - trace_version set from openhands.__version__
            self.assertIn("trace_version", metadata)
            self.assertEqual(metadata["trace_version"], openhands.__version__)

            # session_id should be preserved as string
            self.assertIn("session_id", metadata)
            self.assertEqual(metadata["session_id"], conv_str)

            # trace_user_id should be present
            self.assertIn("trace_user_id", metadata)
            self.assertEqual(metadata["trace_user_id"], user_id)

            # tags should contain expected entries
            tags = metadata.get("tags", [])
            self.assertIn("app:openhands", tags)
            self.assertIn(f"model:{model_name}", tags)
            self.assertIn(f"type:{llm_type}", tags)
            self.assertIn(f"web_host:{os.environ.get('WEB_HOST')}", tags)
            # openhands version should be present in tags as well
            self.assertIn(
                f"openhands_version:{openhands.__version__}",
                tags,
            )
            self.assertIn("conversation_version:V1", tags)

            # Act & Assert - when conversation_id and user_id are None, those keys should be omitted
            metadata2 = get_llm_metadata(model_name, llm_type, conversation_id=None, user_id=None)
            self.assertNotIn("session_id", metadata2)
            self.assertNotIn("trace_user_id", metadata2)
            # tags should still be present
            self.assertIn("tags", metadata2)
        finally:
            # Cleanup env
            if old_web_host is None:
                os.environ.pop("WEB_HOST", None)
            else:
                os.environ["WEB_HOST"] = old_web_host
