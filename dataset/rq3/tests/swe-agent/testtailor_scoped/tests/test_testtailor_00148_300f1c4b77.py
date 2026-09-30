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
        """Ensure main_single_worker stops iterating when run_instance raises _BreakLoop."""
        # Create RunBatch instance without running __init__
        rb = RunBatch.__new__(RunBatch)

        # Provide minimal attributes used by main_single_worker
        rb._show_progress_bar = False  # avoid entering Live context

        # Construct a minimal agent_config with a model.id so the _model_id property works
        class DummyModel:
            def __init__(self, id_):
                self.id = id_

        class DummyAgentConfig:
            def __init__(self, model):
                self.model = model

        rb.agent_config = DummyAgentConfig(DummyModel("instant_empty_submit"))

        # Provide instances to iterate over
        rb.instances = ["inst_a", "inst_b", "inst_c"]

        # Collect calls to ensure only the first instance was processed
        called = []

        def fake_run_instance(instance):
            called.append(instance)
            # Signal loop break as happens in the real code path
            raise _BreakLoop()

        rb.run_instance = fake_run_instance

        # Simple logger that records last info message
        class DummyLogger:
            def __init__(self):
                self.last = None

            def info(self, *args, **kwargs):
                self.last = args

        rb.logger = DummyLogger()

        # Execute the method under test; should not raise and should stop after first instance
        rb.main_single_worker()

        # Assertions: only the first instance was handled and logger was called with expected message
        self.assertEqual(len(called), 1)
        self.assertEqual(called[0], "inst_a")
        self.assertIsNotNone(rb.logger.last)
        self.assertIn("Stopping loop over instances", rb.logger.last[0])
