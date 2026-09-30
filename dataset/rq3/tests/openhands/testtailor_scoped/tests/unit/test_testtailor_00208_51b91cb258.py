import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.llm.debug_mixin')
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
        """Test that log_prompt converts a single dict message into a list and
        builds the debug_message by joining formatted message contents,
        skipping messages with content == None."""
        # local imports via __import__ to avoid adding top-level import statements
        mock_mod = __import__('unittest.mock', fromlist=['MagicMock', 'patch'])
        MagicMock = mock_mod.MagicMock
        patch = mock_mod.patch

        dm = __import__('openhands.llm.debug_mixin', fromlist=['DebugMixin', 'MESSAGE_SEPARATOR'])
        DebugMixin = dm.DebugMixin
        MESSAGE_SEPARATOR = dm.MESSAGE_SEPARATOR

        # A small concrete class implementing the required vision_is_active
        class Dummy(DebugMixin):
            def vision_is_active(self) -> bool:
                return False

        # Patch the module-level loggers so we can assert what gets logged
        with patch('openhands.llm.debug_mixin.logger') as mock_logger, patch(
            'openhands.llm.debug_mixin.llm_prompt_logger'
        ) as mock_prompt_logger:
            # Ensure the method proceeds past the isEnabledFor(DEBUG) check
            mock_logger.isEnabledFor.return_value = True
            # Provide debug attributes as MagicMocks to capture calls
            mock_logger.debug = MagicMock()
            mock_prompt_logger.debug = MagicMock()

            d = Dummy()

            # Case 1: pass a single message dict (not a list) with content as a list
            message_dict = {'role': 'user', 'content': [{'text': 'hello'}, {'text': 'world'}]}
            d.log_prompt(message_dict)

            # _format_message_content should turn the content list into "hello\nworld"
            mock_prompt_logger.debug.assert_called_once_with('hello\nworld')
            mock_logger.debug.assert_not_called()

            # Reset mocks for the next sub-case
            mock_prompt_logger.debug.reset_mock()
            mock_logger.debug.reset_mock()

            # Case 2: pass a list with one message having content None and another valid message
            messages = [{'role': 'system', 'content': None}, {'role': 'assistant', 'content': 'Only'}]
            d.log_prompt(messages)

            # The message with content None should be filtered out and only "Only" logged
            mock_prompt_logger.debug.assert_called_once_with('Only')
            mock_logger.debug.assert_not_called()
