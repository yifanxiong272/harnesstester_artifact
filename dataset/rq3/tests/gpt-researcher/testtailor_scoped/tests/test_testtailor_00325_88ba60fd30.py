import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.actions.agent_creator')
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
        """Ensure that when json_repair.loads raises and response is truthy,
        the debug log containing the truncated response is emitted and the
        function falls back to the default agent.
        """
        response = "x" * 600  # longer than 500 to exercise the truncation in the log

        # Patch json_repair.loads to raise so we hit the except branch that logs and then
        # triggers the debug message with the truncated response.
        with patch.object(json_repair, "loads", side_effect=ValueError("invalid json")):
            # Capture logs at DEBUG level so we can assert the debug message was emitted.
            with self.assertLogs(logger.name, level="DEBUG") as cm:
                # Use dynamic import to avoid needing an explicit asyncio import at top-level
                loop = __import__("asyncio").get_event_loop()
                result = loop.run_until_complete(handle_json_error(response))

        # The function should fall back to the default agent tuple
        self.assertEqual(result[0], "Default Agent")
        self.assertIn("You are an AI critical thinker", result[1])

        # Construct expected truncated debug message and assert it appears in the logs
        expected_debug = f"LLM response that failed to parse: {response[:500]}..."
        assert any(expected_debug in log_msg for log_msg in cm.output), f"Expected debug log not found. Logs: {cm.output}"
