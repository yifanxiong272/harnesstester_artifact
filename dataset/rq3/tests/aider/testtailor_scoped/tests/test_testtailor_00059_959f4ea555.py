import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.single_wholefile_func_coder')
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
        """When edited is True, the coder should append the redacted_edit_message as an assistant reply."""
        # create instance without running __init__ to avoid base class requirements
        coder = object.__new__(SingleWholeFileFunctionCoder)

        # prepare minimal attributes used by the method
        coder.cur_messages = [{"role": "user", "content": "original"}]
        class DummyPrompts:
            pass
        coder.gpt_prompts = DummyPrompts()
        coder.gpt_prompts.redacted_edit_message = "REDACTED EDIT MESSAGE"
        coder.partial_response_content = "SHOULD NOT BE_USED"

        # call method with edited=True to hit the target branch
        coder.add_assistant_reply_to_cur_messages(edited=True)

        # verify that an assistant message with the redacted edit message was appended
        self.assertEqual(len(coder.cur_messages), 2)
        self.assertEqual(
            coder.cur_messages[-1],
            {"role": "assistant", "content": "REDACTED EDIT MESSAGE"},
        )
