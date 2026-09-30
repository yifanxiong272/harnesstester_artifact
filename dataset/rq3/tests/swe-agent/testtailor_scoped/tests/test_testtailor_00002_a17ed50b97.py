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
        """Ensure get_retry_loop_from_config delegates to config.get_retry_loop and returns its result."""
        sentinel = object()

        class DummyConfig:
            def __init__(self):
                self.called_with = None

            # require keyword-only argument to ensure caller uses the keyword
            def get_retry_loop(self, *, problem_statement):
                self.called_with = problem_statement
                return sentinel

        class DummyProblemStatement:
            id = "pid"

            def get_problem_statement(self) -> str:
                return "describe the problem"

            def get_extra_fields(self) -> dict:
                return {"foo": "bar"}

        cfg = DummyConfig()
        ps = DummyProblemStatement()

        result = get_retry_loop_from_config(config=cfg, problem_statement=ps)

        # The returned object should be exactly what the config returned
        self.assertIs(result, sentinel)
        # And the config should have been called with our problem statement
        self.assertIs(cfg.called_with, ps)
