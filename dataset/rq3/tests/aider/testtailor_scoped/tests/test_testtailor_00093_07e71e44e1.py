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
        """When edited is False, the assistant partial response content is appended to cur_messages."""
        # Grab the unbound method so we can call it with a fake self
        fn = SingleWholeFileFunctionCoder.add_assistant_reply_to_cur_messages

        class Fake: 
            pass

        fake = Fake()
        # start with an existing message to ensure += behavior (appending)
        fake.cur_messages = [dict(role="user", content="hello")]
        fake.partial_response_content = "partial reply"

        # Call method with edited=False to exercise the target branch
        fn(fake, edited=False)

        # Expect the assistant reply with partial_response_content to be appended
        self.assertEqual(len(fake.cur_messages), 2)
        self.assertDictEqual(
            fake.cur_messages[1],
            dict(role="assistant", content="partial reply"),
        )
