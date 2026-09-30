import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.wholefile_func_coder')
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
        """When edited is True, the redacted_edit_message is appended to cur_messages."""
        # create instance without calling __init__ to avoid RuntimeError in constructor
        coder = object.__new__(WholeFileFunctionCoder)

        # prepare minimal required attributes used by the method
        coder.cur_messages = []
        class GP:
            pass
        coder.gpt_prompts = GP()
        coder.gpt_prompts.redacted_edit_message = "REDACTED_EDIT_MESSAGE"
        coder.partial_response_content = "SHOULD_NOT_BE_USED"

        # call the method under test with edited=True to take the target branch
        coder.add_assistant_reply_to_cur_messages(edited=True)

        # verify that the assistant redacted message was appended
        self.assertEqual(
            coder.cur_messages,
            [dict(role="assistant", content="REDACTED_EDIT_MESSAGE")]
        )
