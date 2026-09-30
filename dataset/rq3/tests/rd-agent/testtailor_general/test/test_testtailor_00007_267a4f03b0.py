import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.data_science.proposal.exp_gen.proposal')
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
        """Ensure get_component reads from _COMPONENT_META and raises for unknown names."""
        import inspect

        # find the module where get_component is defined so we can patch its globals
        mod = inspect.getmodule(get_component)
        self.assertIsNotNone(mod, "Failed to locate module for get_component")

        name = "test_component_xx"
        meta_entry = {
            "target_name": "my_target",
            "spec_file": "/tmp/spec.yaml",
            "output_format_key": "fmt_key",
            "task_class": dict,
        }

        # backup original values to restore after the test
        orig_meta_val = None
        had_orig = False
        if hasattr(mod, "_COMPONENT_META"):
            orig_meta_val = dict(mod._COMPONENT_META)  # shallow copy
            had_orig = True
        orig_T = getattr(mod, "T", None)

        # create a dummy T class to control .r() output
        class DummyT:
            def __init__(self, key):
                self.key = key

            def r(self):
                return f"FORMAT:{self.key}"

        try:
            # inject our test meta and DummyT into the module under test
            if not hasattr(mod, "_COMPONENT_META") or not isinstance(mod._COMPONENT_META, dict):
                mod._COMPONENT_META = {}
            mod._COMPONENT_META[name] = meta_entry
            mod.T = DummyT

            # call the function for an existing component
            result = get_component(name)
            self.assertIsInstance(result, dict)
            self.assertEqual(result["target_name"], meta_entry["target_name"])
            self.assertEqual(result["spec_file"], meta_entry["spec_file"])
            self.assertEqual(result["task_output_format"], DummyT(meta_entry["output_format_key"]).r())
            self.assertEqual(result["task_class"], meta_entry["task_class"])

            # calling with an unknown name should raise KeyError (covers meta = _COMPONENT_META.get(name) returning None)
            with self.assertRaises(KeyError):
                get_component("non_existent_component_zz")
        finally:
            # restore original module state
            if had_orig:
                mod._COMPONENT_META.clear()
                mod._COMPONENT_META.update(orig_meta_val)
            else:
                if hasattr(mod, "_COMPONENT_META"):
                    try:
                        delattr(mod, "_COMPONENT_META")
                    except Exception:
                        pass
            if orig_T is not None:
                mod.T = orig_T
            else:
                if hasattr(mod, "T"):
                    try:
                        delattr(mod, "T")
                    except Exception:
                        pass
