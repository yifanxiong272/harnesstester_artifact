import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.data_science.proposal.exp_gen.naive')
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
        """Find NaiveExpGen implementation, patch prompts/builder, and exercise gen to produce DSExperiment."""
        import importlib
        import pkgutil
        from types import SimpleNamespace
        from unittest.mock import patch

        # Locate the module that defines NaiveExpGen under the exp_gen package
        pkg_name = "rdagent.scenarios.data_science.proposal.exp_gen"
        pkg = importlib.import_module(pkg_name)
        NaiveExpGen = None
        target_module = None

        for finder, mod_name, ispkg in pkgutil.iter_modules(pkg.__path__):
            full_mod_name = f"{pkg_name}.{mod_name}"
            try:
                mod = importlib.import_module(full_mod_name)
            except Exception:
                continue
            if hasattr(mod, "NaiveExpGen"):
                NaiveExpGen = getattr(mod, "NaiveExpGen")
                target_module = mod
                break

        # fallback: try the base module directly if not found above
        if NaiveExpGen is None:
            try:
                mod = importlib.import_module(f"{pkg_name}.base")
                if hasattr(mod, "NaiveExpGen"):
                    NaiveExpGen = getattr(mod, "NaiveExpGen")
                    target_module = mod
            except Exception:
                pass

        self.assertIsNotNone(NaiveExpGen, "Could not find NaiveExpGen implementation in exp_gen package")

        # Dummy translation helper to produce deterministic prompts
        class DummyT:
            def __init__(self, key):
                self.key = key

            def r(self, **kwargs):
                # Return a simple identifiable string so the prompts are deterministic
                return f"{self.key}|{kwargs}"

        # Create a fake task object that the builder will return
        fake_task = SimpleNamespace(description="fake pipeline description")

        # Build a minimal trace-like object fulfilling the methods used by gen()
        trace = SimpleNamespace()
        trace.sota_experiment = lambda: None
        trace.scen = SimpleNamespace(get_scenario_all_desc=lambda: "dummy scenario description")
        trace.experiment_and_feedback_list_after_init = lambda return_type="all": []

        # Patch T and build_cls_from_json_with_retry in the module where NaiveExpGen is defined
        assert target_module is not None
        with patch.object(target_module, "T", DummyT), patch.object(
            target_module, "build_cls_from_json_with_retry", lambda *args, **kwargs: fake_task
        ):
            # Instantiate and call gen
            try:
                gen_inst = NaiveExpGen()
            except Exception:
                # If NaiveExpGen requires special init, create an instance without calling __init__
                gen_inst = object.__new__(NaiveExpGen)
            exp = gen_inst.gen(trace)

        # Verify the returned experiment uses our fake task and its description became the hypothesis
        self.assertIsNotNone(exp)
        self.assertTrue(hasattr(exp, "pending_tasks_list"))
        self.assertIsInstance(exp.pending_tasks_list, list)
        self.assertGreater(len(exp.pending_tasks_list), 0)
        self.assertGreater(len(exp.pending_tasks_list[0]), 0)
        self.assertIs(exp.pending_tasks_list[0][0], fake_task)
        self.assertTrue(hasattr(exp, "hypothesis"))
        self.assertEqual(exp.hypothesis.hypothesis, "fake pipeline description")
