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
        """When edited is False, append partial_response_content as an assistant message."""
        class DummySelf:
            pass

        dummy = DummySelf()
        # start with an existing message to ensure we append
        dummy.cur_messages = [{"role": "system", "content": "initial"}]
        dummy.partial_response_content = "partial reply content"

        # Call the unbound method with our dummy object and edited=False
        WholeFileFunctionCoder.add_assistant_reply_to_cur_messages(dummy, edited=False)

        # Verify that a new assistant message was appended with the partial content
        self.assertEqual(len(dummy.cur_messages), 2)
        self.assertEqual(
            dummy.cur_messages[-1],
            {"role": "assistant", "content": "partial reply content"},
        )
