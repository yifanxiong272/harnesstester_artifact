import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.storage.conversation.conversation_validator')
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
        """Ensure create_conversation_validator uses the environment default and get_impl correctly."""
        class DummyCV:
            def __init__(self):
                # simple marker to show construction happened
                self._constructed = True

        with patch('openhands.storage.conversation.conversation_validator.get_impl') as mock_get_impl:
            mock_get_impl.return_value = DummyCV
            # Ensure the environment variable is not set so the default is used
            with patch.dict('os.environ', {}, clear=True):
                from openhands.storage.conversation import conversation_validator as cv_mod

                inst = cv_mod.create_conversation_validator()

                # Returned instance should be an instance of the class returned by our mocked get_impl
                self.assertIsInstance(inst, DummyCV)

                # Verify get_impl was called with the ConversationValidator base class and the default FQCN
                mock_get_impl.assert_called_once()
                called_args = mock_get_impl.call_args[0]
                # first arg should be the ConversationValidator class defined in the module
                self.assertIs(called_args[0], cv_mod.ConversationValidator)
                # second arg should be the default fully-qualified class name string
                self.assertEqual(
                    called_args[1],
                    'openhands.storage.conversation.conversation_validator.ConversationValidator',
                )
