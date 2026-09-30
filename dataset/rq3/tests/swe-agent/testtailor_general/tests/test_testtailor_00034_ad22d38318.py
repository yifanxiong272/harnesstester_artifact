import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.run_single')
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
        """Ensure run_from_config calls RunSingle.from_config and then run() on the returned instance."""
        # import inside the test as requested
        from sweagent.run.run_single import run_from_config, RunSingle
        from unittest.mock import patch

        config = object()
        called = {"ran": False}

        class DummyRunSingle:
            def run(self):
                called["ran"] = True

        # Patch the classmethod RunSingle.from_config to return our dummy instance
        with patch.object(RunSingle, "from_config", classmethod(lambda cls, cfg: DummyRunSingle())):
            run_from_config(config)

        self.assertTrue(called["ran"], "Expected RunSingle.run() to be called by run_from_config")
