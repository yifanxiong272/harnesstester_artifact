import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.service')
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
        """Ensure log_response uses module logger when logger is None and logs all parts."""
        # Import the function under test from the likely modules (fall back if needed)
        try:
            from browser_use.agent.service import log_response  # primary expected location
        except Exception:
            from browser_use.beta.service import log_response  # fallback

        import logging
        from unittest.mock import patch

        # Build a minimal dummy response object with the expected .current_state attributes
        class DummyCurrentState:
            def __init__(self, thinking, evaluation_previous_goal, memory, next_goal):
                self.thinking = thinking
                self.evaluation_previous_goal = evaluation_previous_goal
                self.memory = memory
                self.next_goal = next_goal

        class DummyResponse:
            def __init__(self, current_state):
                self.current_state = current_state

        dummy = DummyResponse(
            DummyCurrentState(
                thinking='Some internal reasoning text.',
                evaluation_previous_goal='Success: all checks passed',
                memory='Important facts to remember.',
                next_goal='Wrap up and finish',
            )
        )

        # Capture logger calls/messages
        recorded = []

        class RecordingLogger:
            def debug(self, msg, *args, **kwargs):
                recorded.append(('debug', msg))

            def info(self, msg, *args, **kwargs):
                recorded.append(('info', msg))

        # Patch logging.getLogger so that when log_response calls it (because logger is None)
        # we return our RecordingLogger and can inspect what was logged.
        with patch.object(logging, 'getLogger', return_value=RecordingLogger()) as mock_get_logger:
            # Call with logger=None to force the code path that uses logging.getLogger(__name__)
            log_response(dummy, registry=None, logger=None)

            # Ensure the module attempted to resolve a logger
            self.assertTrue(mock_get_logger.called)

        # Verify that the expected pieces were logged
        kinds = [k for k, _ in recorded]
        messages = [m for _, m in recorded]

        # There should be at least one debug (thinking) and multiple info entries
        self.assertIn('debug', kinds)
        self.assertIn('info', kinds)

        # Check message content substrings for each section
        # Thinking should have been logged at debug level
        self.assertTrue(any('Thinking' in (m or '') or '💡' in (m or '') for m in messages))
        # Evaluation should include Eval and the success emoji (thumbs up) rendered
        self.assertTrue(any('Eval:' in (m or '') and 'Success' in (m or '') or '👍' in (m or '') for m in messages))
        # Memory should include the brain emoji or 'Memory'
        self.assertTrue(any('Memory' in (m or '') or '🧠' in (m or '') for m in messages))
        # Next goal should include 'Next goal' or the target emoji
        self.assertTrue(any('Next goal' in (m or '') or '🎯' in (m or '') for m in messages))
