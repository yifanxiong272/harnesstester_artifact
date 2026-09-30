import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.utils.agent.workflow')
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
        """Test that build_cls_from_json_with_retry retries on invalid JSON and returns an instance on success."""
        # simple class to be constructed from JSON response
        class Dummy:
            def __init__(self, name):
                self.name = name

        # Prepare the APIBackend mock: first call returns invalid JSON, second returns valid JSON
        with unittest.mock.patch("rdagent.oai.llm_utils.APIBackend") as MockBackend:
            MockBackend.return_value.build_messages_and_create_chat_completion.side_effect = [
                "this is not json",
                json.dumps({"name": "Alice"}),
            ]

            # Call the function under test
            result = build_cls_from_json_with_retry(
                Dummy, system_prompt="sys", user_prompt="usr", retry_n=3
            )

            # Assertions
            self.assertIsInstance(result, Dummy)
            self.assertEqual(result.name, "Alice")
            # Ensure the backend was called twice (one failure, one success)
            self.assertEqual(
                MockBackend.return_value.build_messages_and_create_chat_completion.call_count, 2
            )
