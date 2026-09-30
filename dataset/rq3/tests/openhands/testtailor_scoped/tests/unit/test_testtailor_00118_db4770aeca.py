import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.utils.conversation_summary')
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
        """Ensure messages longer than 1000 chars are truncated with the marker before sending to LLM."""
        long_message = 'x' * 1005  # > 1000 to trigger truncation

        captured = {}

        class DummyRegistry:
            def request_extraneous_completion(self, service_id, llm_config, messages):
                # capture the messages passed in for assertions
                captured['service_id'] = service_id
                captured['llm_config'] = llm_config
                captured['messages'] = messages
                return 'Generated Title'

        dummy_registry = DummyRegistry()

        # Create the coroutine (do not use asyncio.run to avoid needing imports)
        coro = generate_conversation_title(long_message, llm_config='dummy_cfg', llm_registry=dummy_registry, max_length=50)

        # Drive the coroutine to completion manually (it contains no awaits, so this will run to completion)
        try:
            result = coro.send(None)
        except StopIteration as e:
            result = e.value

        # Ensure we got the stubbed title back
        self.assertEqual(result, 'Generated Title')

        # Inspect the prompt passed to the registry to verify truncation occurred
        self.assertIn('messages', captured)
        user_content = captured['messages'][1]['content']

        # The truncated message should be appended after a blank line in the user prompt
        split_idx = user_content.find('\n\n')
        self.assertNotEqual(split_idx, -1, "Expected prompt to contain a double newline before the message")

        truncated_part = user_content[split_idx + 2 :]
        # It should end with the truncation marker
        self.assertTrue(truncated_part.endswith('...(truncated)'))
        # And its length should be exactly 1000 + len('...(truncated)')
        self.assertEqual(len(truncated_part), 1000 + len('...(truncated)'))
        # And the start of the truncated part should match the original message's start
        self.assertTrue(truncated_part.startswith('x' * 10))  # sanity check on content start
