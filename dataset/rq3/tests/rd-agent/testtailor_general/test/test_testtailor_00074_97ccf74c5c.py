import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.app.qlib_rd_loop.quant')
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
        """Ensure QuantRDLoop is constructed when path is None and its run() is awaited."""
        import importlib

        mod = importlib.import_module("rdagent.app.qlib_rd_loop.quant")

        called = {}

        class FakeQuantRDLoop:
            def __init__(self, prop_setting):
                # record that constructor was called with the module's QUANT_PROP_SETTING
                called["instantiated_with"] = prop_setting

            async def run(self, **kwargs):
                # record that run was called and with which kwargs
                called["run_called_with"] = kwargs

        # Patch the module to use the fake class and ensure QUANT_PROP_SETTING exists
        setattr(mod, "QuantRDLoop", FakeQuantRDLoop)
        setattr(mod, "QUANT_PROP_SETTING", "SENTINEL_SETTING")

        # Call main with path=None to trigger QuantRDLoop(QUANT_PROP_SETTING)
        mod.main(path=None)

        # Assertions: constructor used module QUANT_PROP_SETTING and run was called with defaults
        self.assertEqual(called.get("instantiated_with"), "SENTINEL_SETTING")
        self.assertIn("run_called_with", called)
        self.assertEqual(
            called["run_called_with"],
            {"step_n": None, "loop_n": None, "all_duration": None},
        )
