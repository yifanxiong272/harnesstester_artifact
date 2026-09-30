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
        """Ensure constructing RunBatch raises when model is 'human' and num_workers > 1.

        The RunBatch.__init__ checks self._model_id very early. To make that property
        return 'human' before instance attributes are set, we temporarily set a class
        attribute `agent_config` on RunBatch so the property finds it via attribute lookup.
        """
        # Create simple dummy objects with the expected attributes
        class _M:
            def __init__(self, id_):
                self.id = id_

        class _AgentCfg:
            def __init__(self, model):
                self.model = model

        dummy_agent_cfg = _AgentCfg(_M("human"))

        # Keep track of original class attribute so we can restore it
        had_attr = hasattr(RunBatch, "agent_config")
        original = getattr(RunBatch, "agent_config", None)
        try:
            # Monkeypatch class attribute so self._model_id resolves to "human"
            RunBatch.agent_config = dummy_agent_cfg

            # Provide >1 instances and num_workers > 1 to trigger the guard
            instances = [object(), object()]
            with self.assertRaises(ValueError) as cm:
                # We pass agent_config=None as parameter to ensure the constructor path is exercised;
                # the class attribute causes the early check to see "human".
                RunBatch(instances=instances, agent_config=None, num_workers=2)

            self.assertIn("Cannot run with human model in parallel", str(cm.exception))
        finally:
            # Restore original state
            if had_attr:
                RunBatch.agent_config = original
            else:
                delattr(RunBatch, "agent_config")
