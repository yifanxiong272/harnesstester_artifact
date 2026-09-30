import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.factor_coder.__init__')
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
        """Instantiate FactorCoSTEER while patching heavy dependencies to hit its __init__ path."""
        try:
            import importlib
            import types

            # Import the module that defines FactorCoSTEER
            mod = importlib.import_module("rdagent.components.coder.factor_coder")

            # Patch heavy dependencies in the module to lightweight stubs
            # 1) Minimal settings object
            mod.FACTOR_COSTEER_SETTINGS = types.SimpleNamespace(coder_use_cache=False, v2_error_summary=False)

            # 2) Simple stub for FactorEvaluatorForCoder
            class _StubFactorEvaluatorForCoder:
                def __init__(self, scen=None):
                    self.scen = scen

            mod.FactorEvaluatorForCoder = _StubFactorEvaluatorForCoder

            # 3) Simple stub for CoSTEERMultiEvaluator
            class _StubCoSTEERMultiEvaluator:
                def __init__(self, single_evaluator, scen=None):
                    self.single_evaluator = single_evaluator
                    self.scen = scen

            mod.CoSTEERMultiEvaluator = _StubCoSTEERMultiEvaluator

            # 4) Simple stub for FactorMultiProcessEvolvingStrategy
            class _StubFactorMultiProcessEvolvingStrategy:
                def __init__(self, scen=None, settings=None, *args, **kwargs):
                    self.scen = scen
                    self.settings = settings

            mod.FactorMultiProcessEvolvingStrategy = _StubFactorMultiProcessEvolvingStrategy

            # Patch the base class __init__ to be a no-op so super().__init__ won't execute heavy logic
            base = mod.FactorCoSTEER.__mro__[1]  # the direct base class (CoSTEER)
            orig_base_init = getattr(base, "__init__", None)

            def _dummy_base_init(self, *args, **kwargs):
                # simply record what was passed for lightweight verification
                self._init_args = args
                self._init_kwargs = kwargs

            base.__init__ = _dummy_base_init  # monkeypatch

            # Create a minimal Scenario implementation required by FactorCoSTEER
            from rdagent.core.scenario import Scenario

            class DummyScenario(Scenario):
                @property
                def background(self) -> str:
                    return "dummy background"

                @property
                def rich_style_description(self) -> str:
                    return "rich style"

                # avoid importing Task type by not using it in annotation
                def get_scenario_all_desc(self, task=None, filtered_tag: str | None = None, simple_background: bool | None = None) -> str:
                    return "scenario all desc"

                def get_runtime_environment(self) -> str:
                    return "runtime env"

            scen = DummyScenario()

            # Instantiate FactorCoSTEER which should exercise the target __init__ code paths
            fc = mod.FactorCoSTEER(scen=scen)

            # Basic assertions to ensure object constructed and base __init__ was called (monkeypatched)
            self.assertIsInstance(fc, mod.FactorCoSTEER)
            self.assertTrue(hasattr(fc, "_init_kwargs"))
            self.assertIn("settings", fc._init_kwargs)
            self.assertIn("eva", fc._init_kwargs)
            self.assertIn("es", fc._init_kwargs)
            self.assertEqual(fc._init_kwargs.get("evolving_version"), 2)
        except Exception as e:
            self.fail(f"Unexpected exception during test execution: {e}")
        finally:
            # restore original base init to avoid side effects
            try:
                if 'base' in locals() and orig_base_init is not None:
                    base.__init__ = orig_base_init
            except Exception:
                pass
