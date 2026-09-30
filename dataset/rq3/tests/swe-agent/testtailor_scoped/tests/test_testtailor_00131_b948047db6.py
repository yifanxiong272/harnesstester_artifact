import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.reviewer')
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
        """Ensure ChooserRetryLoopConfig.get_retry_loop returns a ChooserRetryLoop instance."""
        # Minimal ProblemStatement implementation
        class DummyProblemStatement:
            id = "dummy"

            def get_problem_statement(self) -> str:
                return "solve this"

            def get_extra_fields(self) -> dict[str, object]:
                return {}

        ps = DummyProblemStatement()

        # Create a ChooserRetryLoopConfig instance without pydantic validation to avoid
        # having to construct a full ChooserConfig (which has many required fields).
        # pydantic v2 provides model_construct to build a model instance without validation.
        cfg = ChooserRetryLoopConfig.model_construct(
            chooser=object(),  # placeholder; real Chooser will be monkeypatched below
            max_attempts=3,
            min_budget_for_new_attempt=0.0,
            cost_limit=10.0,
        )

        # Monkeypatch the Chooser class used inside ChooserRetryLoop so constructing the loop
        # does not require the real, complex ChooserConfig/Chooser classes.
        module_name = ChooserRetryLoop.__module__
        mod = __import__(module_name, fromlist=["Chooser"])
        orig_Chooser = getattr(mod, "Chooser", None)

        class DummyChooser:
            def __init__(self, cfg):
                self.cfg = cfg

            def choose(self, problem_statement, submissions):
                # Return an object with chosen_idx attribute if ever called.
                return type("R", (), {"chosen_idx": None})()

        setattr(mod, "Chooser", DummyChooser)
        try:
            loop = cfg.get_retry_loop(ps)

            # Verify that the returned object is the expected type and contains our inputs.
            self.assertIsInstance(loop, ChooserRetryLoop)
            self.assertIs(loop._problem_statement, ps)
            self.assertIs(loop._config, cfg)
        finally:
            # Restore original Chooser to avoid side effects on other tests.
            if orig_Chooser is None:
                try:
                    delattr(mod, "Chooser")
                except Exception:
                    # If deletion fails for some reason, ignore to avoid masking test result.
                    pass
            else:
                setattr(mod, "Chooser", orig_Chooser)
