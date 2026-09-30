import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.models')
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
        """Ensure AbstractModel.reset_stats replaces any existing stats with a fresh InstanceStats"""
        # create a minimal concrete subclass of AbstractModel
        class DummyModel(AbstractModel):
            def __init__(self):
                # types are only annotations in AbstractModel.__init__, so None is fine at runtime
                super().__init__(config=None, tools=None)

            def query(self, history, action_prompt: str = "> ") -> dict:
                return {}

        m = DummyModel()

        # set a non-default stats object to ensure reset actually replaces it
        m.stats = InstanceStats(instance_cost=3.14, tokens_sent=10, tokens_received=5, api_calls=2)
        old_id = id(m.stats)

        # call the method under test
        m.reset_stats()

        # new stats object was created
        self.assertTrue(hasattr(m, "stats"))
        self.assertIsInstance(m.stats, InstanceStats)
        self.assertNotEqual(id(m.stats), old_id)

        # all fields should be reset to their defaults (zeros)
        self.assertEqual(m.stats.instance_cost, 0)
        self.assertEqual(m.stats.tokens_sent, 0)
        self.assertEqual(m.stats.tokens_received, 0)
        self.assertEqual(m.stats.api_calls, 0)
