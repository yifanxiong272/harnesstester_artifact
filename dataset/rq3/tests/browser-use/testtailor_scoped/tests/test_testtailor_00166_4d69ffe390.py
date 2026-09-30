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
        """Log a failure evaluation and ensure red failure branch is used."""
        # Local imports so top-level test file doesn't need to include them
        import logging
        from browser_use.agent.views import AgentOutput
        from browser_use.tools.registry.views import ActionModel
        from browser_use.agent.service import log_response

        class RecordingLogger:
            def __init__(self):
                self.infos = []
                self.debugs = []

            def info(self, message, *args, **kwargs):
                self.infos.append(message)

            def debug(self, message, *args, **kwargs):
                self.debugs.append(message)

            def isEnabledFor(self, level):
                # mimic a logger that might not have debug enabled
                return False

        logger = RecordingLogger()

        # Prepare an AgentOutput with an evaluation that contains "failure" but not "success"
        eval_goal = "Failure: could not complete the step"
        output = AgentOutput(
            evaluation_previous_goal=eval_goal,
            memory="some important memory",
            next_goal="Finish up",
            thinking=None,
            action=[ActionModel()],
        )

        # Invoke the function under test
        log_response(output, logger=logger)

        # Assert that an Eval message was logged and that it used the red color + warning emoji
        eval_messages = [m for m in logger.infos if 'Eval:' in m]
        self.assertTrue(eval_messages, "Expected at least one Eval log message")
        matched = False
        for msg in eval_messages:
            if '\033[31m' in msg and '⚠️' in msg and eval_goal in msg:
                matched = True
                break
        self.assertTrue(matched, f"Expected red failure Eval log with emoji, got: {eval_messages}")

        # Also assert memory was logged
        memory_messages = [m for m in logger.infos if '🧠 Memory' in m]
        self.assertTrue(memory_messages, "Expected memory to be logged")
