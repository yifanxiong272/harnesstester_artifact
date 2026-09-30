import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.run_batch')
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
        """Initializing RunBatch with a human model and num_workers > 1 should raise."""
        # Prepare a dummy agent config with model.id == "human".
        dummy_agent = type("A", (), {"model": type("M", (), {"id": "human"})()})()
        # Temporarily set class-level agent_config so that _model_id property
        # returns "human" before the instance attribute is assigned in __init__.
        old_agent_config = getattr(RunBatch, "agent_config", None)
        try:
            RunBatch.agent_config = dummy_agent
            with self.assertRaises(ValueError) as cm:
                # num_workers > 1 should trigger the ValueError for human model
                RunBatch(instances=[object()], agent_config=dummy_agent, num_workers=2)
            self.assertEqual(str(cm.exception), "Cannot run with human model in parallel")
        finally:
            # Restore previous class attribute to avoid side effects on other tests
            if old_agent_config is None:
                delattr(RunBatch, "agent_config")
            else:
                RunBatch.agent_config = old_agent_config
