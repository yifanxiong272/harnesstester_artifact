import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.log.ui.ds_summary')
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
        """Call curves_win so the st.columns(2) assignment is executed."""
        import sys
        import types
        import inspect

        # Find the module that defines curves_win
        target_mod = None
        for m in list(sys.modules.values()):
            if not isinstance(m, types.ModuleType):
                continue
            if hasattr(m, "curves_win") and inspect.isfunction(getattr(m, "curves_win")):
                target_mod = m
                break

        self.assertIsNotNone(target_mod, "Could not find a module exposing curves_win")

        # Create a fake streamlit-like object where columns(2) returns two column objects
        class FakeCol:
            def __init__(self, name):
                self.name = name
                self.toggled = False

            def toggle(self, *args, **kwargs):
                # Return False so curves_win does not enter the heavier rendering branches
                self.toggled = True
                return False

        class FakeSt:
            def __init__(self):
                self.columns_called = False

            def columns(self, n):
                self.columns_called = True
                return (FakeCol("c1"), FakeCol("c2"))

        fake_st = FakeSt()

        # Monkeypatch the module's st to our fake
        original_st = getattr(target_mod, "st", None)
        setattr(target_mod, "st", fake_st)
        try:
            # Call curves_win with an empty summary (since toggles return False,
            # the function will only execute the columns assignment and toggles)
            target_mod.curves_win({})
        finally:
            # restore original st to avoid side effects
            if original_st is None:
                delattr(target_mod, "st")
            else:
                setattr(target_mod, "st", original_st)

        # Verify our fake columns was invoked
        self.assertTrue(fake_st.columns_called)
