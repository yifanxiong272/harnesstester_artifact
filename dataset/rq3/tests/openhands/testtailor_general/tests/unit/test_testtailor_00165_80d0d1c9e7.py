import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.critic.finish_critic')
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
        critic = AgentFinishedCritic()
        self.assertIsInstance(critic, AgentFinishedCritic)

        # No events -> should report agent did not finish.
        res = critic.evaluate(events=[], git_patch=None)
        self.assertEqual(res.score, 0)
        self.assertEqual(res.message, 'Agent did not finish.')

        # Non-finishing action should result in "Agent did not finish."
        class DummyAction(Action):
            pass

        res = critic.evaluate(events=[DummyAction()], git_patch=None)
        self.assertEqual(res.score, 0)
        self.assertEqual(res.message, 'Agent did not finish.')

        # AgentFinishAction should report finished.
        res = critic.evaluate(events=[DummyAction(), AgentFinishAction()], git_patch=None)
        self.assertEqual(res.score, 1)
        self.assertEqual(res.message, 'Agent finished.')

        # Empty git patch (only whitespace) should override and return score 0 with appropriate message.
        res = critic.evaluate(events=[AgentFinishAction()], git_patch='   ')
        self.assertEqual(res.score, 0)
        self.assertEqual(res.message, 'Git patch is empty.')
