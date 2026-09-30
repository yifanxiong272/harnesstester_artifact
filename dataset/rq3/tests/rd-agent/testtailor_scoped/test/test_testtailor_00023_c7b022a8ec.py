import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.data_science.share.eval')
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
        """Ensure ModelDumpEvaluator.__init__ calls super().__init__ and sets data_type."""
        # Minimal concrete Scenario implementation to satisfy abstract requirements
        class DummyScenario(Scenario):
            @property
            def background(self) -> str:
                return "dummy background"

            @property
            def rich_style_description(self) -> str:
                return "rich description"

            def get_scenario_all_desc(self, task: Task | None = None, filtered_tag: str | None = None, simple_background: bool | None = None) -> str:
                return "all desc"

            def get_runtime_environment(self) -> str:
                return "runtime env"

        scen = DummyScenario()

        # Monkeypatch the immediate base class __init__ to avoid depending on its implementation.
        base = ModelDumpEvaluator.__bases__[0]
        orig_init = getattr(base, "__init__", None)
        try:
            def fake_init(self, scen_arg):
                # emulate expected behavior of setting scen attribute in the real super init
                self.scen = scen_arg

            base.__init__ = fake_init

            # Instantiate with both allowed data_type values and check attributes
            evaluator_full = ModelDumpEvaluator(scen, data_type="full")
            self.assertIs(evaluator_full.scen, scen)
            self.assertEqual(evaluator_full.data_type, "full")

            evaluator_sample = ModelDumpEvaluator(scen, data_type="sample")
            self.assertIs(evaluator_sample.scen, scen)
            self.assertEqual(evaluator_sample.data_type, "sample")
        finally:
            # Restore original __init__ to avoid side effects on other tests
            if orig_init is None:
                try:
                    delattr(base, "__init__")
                except Exception:
                    pass
            else:
                base.__init__ = orig_init
