import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.CoSTEER.__init__')
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
        """Test CoSTEER __init__ sets attributes and selects RAG strategy correctly."""
        # Prepare settings with explicit paths and max_loop
        settings = CoSTEERSettings()
        settings.knowledge_base_path = "/tmp/test_kb"
        settings.new_knowledge_base_path = "/tmp/test_new_kb"
        settings.max_loop = 7

        # Minimal evaluator implementation to satisfy abstract base
        class DummyEvaluator(RAGEvaluator):
            def evaluate(self, eo, queried_knowledge=None):
                return None

        eva = DummyEvaluator()
        es = object()  # evolving strategy can be any object for this test

        # Provide a dummy positional argument required by Developer.__init__
        scen_arg = "dummy_scen"

        # Instantiate with default evolving_version (should pick V2)
        coder = CoSTEER(settings, eva, es, scen_arg)
        self.assertIs(coder.settings, settings)
        self.assertEqual(coder.max_loop, 7)
        # Compare string forms to avoid depending on Path import in this test body
        self.assertEqual(str(coder.knowledge_base_path), "/tmp/test_kb")
        self.assertEqual(str(coder.new_knowledge_base_path), "/tmp/test_new_kb")
        self.assertTrue(coder.with_knowledge)
        self.assertTrue(coder.knowledge_self_gen)
        self.assertIs(coder.evolving_strategy, es)
        self.assertIs(coder.evaluator, eva)
        self.assertEqual(coder.evolving_version, 2)
        # Ensure the selected RAG strategy corresponds to V2 by class name
        self.assertEqual(coder.rag.__class__.__name__, "CoSTEERRAGStrategyV2")

        # Override evolving_version to 1 and other flags; include scen arg again
        coder1 = CoSTEER(
            settings,
            eva,
            es,
            scen_arg,
            evolving_version=1,
            with_knowledge=False,
            knowledge_self_gen=False,
            max_loop=3,
        )
        # Ensure the selected RAG strategy corresponds to V1 by class name
        self.assertEqual(coder1.rag.__class__.__name__, "CoSTEERRAGStrategyV1")
        self.assertEqual(coder1.max_loop, 3)
        self.assertFalse(coder1.with_knowledge)
        self.assertFalse(coder1.knowledge_self_gen)
        self.assertEqual(coder1.evolving_version, 1)
