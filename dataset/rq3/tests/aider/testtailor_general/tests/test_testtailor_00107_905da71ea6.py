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
        """When edited is False, the assistant reply should be appended using partial_response_content."""
        # create instance without calling __init__ because WholeFileFunctionCoder.__init__ raises
        coder = object.__new__(WholeFileFunctionCoder)
        # prepare state expected by the method
        coder.cur_messages = [{"role": "system", "content": "start"}]
        coder.partial_response_content = "partial assistant reply"
        # ensure gpt_prompts exists but it's not used for the False branch
        coder.gpt_prompts = None

        # call with edited == False to exercise the target branch
        coder.add_assistant_reply_to_cur_messages(edited=False)

        # verify that a new assistant message with partial_response_content was appended
        self.assertEqual(len(coder.cur_messages), 2)
        self.assertEqual(
            coder.cur_messages[-1],
            {"role": "assistant", "content": "partial assistant reply"},
        )
