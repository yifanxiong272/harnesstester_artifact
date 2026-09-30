import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.models')
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
        """Ensure get_model_settings_as_yaml produces YAML with defaults and model entries.

        This test monkeypatches dataclasses.fields at runtime to simulate dataclass
        field objects for the module's ModelSettings, populates MODEL_SETTINGS with
        two simple model entries (one differing from defaults), and verifies the
        generated YAML contains the expected default block, model entries, and a
        changed field rendered in YAML.
        """
        # Local imports to avoid relying on top-level imports in this snippet.
        import importlib
        import dataclasses
        import types

        # Import the module under test
        mod = importlib.import_module("aider.models")

        func = getattr(mod, "get_model_settings_as_yaml")

        # Prepare holders for restoring state
        orig_dataclasses_fields = None
        orig_model_settings = None

        # Build fake dataclass field objects from ModelSettings annotations and defaults
        try:
            annotations = getattr(mod.ModelSettings, "__annotations__", {})
            fake_fields = []
            for name in annotations:
                default_val = getattr(mod.ModelSettings, name, dataclasses.MISSING)
                # Simple object with .name and .default attributes
                fake_fields.append(types.SimpleNamespace(name=name, default=default_val))

            # Save original dataclasses.fields and monkeypatch it
            orig_dataclasses_fields = dataclasses.fields
            dataclasses.fields = lambda cls: fake_fields

            # Prepare base attributes for model instances (use defaults where provided)
            base_attrs = {}
            for f in fake_fields:
                if f.default is dataclasses.MISSING:
                    base_attrs[f.name] = None
                else:
                    base_attrs[f.name] = f.default

            # Create two model entries. One will differ from the defaults to ensure
            # that a field is included in the YAML output.
            model_a = dict(base_attrs)
            model_a["name"] = "model-a"
            # Flip a boolean default to ensure it's included (e.g., lazy default is False)
            model_a["lazy"] = True

            model_b = dict(base_attrs)
            model_b["name"] = "model-b"
            # Keep all defaults for model_b

            # Swap in our MODEL_SETTINGS, preserving original to restore later
            orig_model_settings = getattr(mod, "MODEL_SETTINGS", None)
            mod.MODEL_SETTINGS = [types.SimpleNamespace(**model_a), types.SimpleNamespace(**model_b)]

            # Call the function under test
            yaml_str = func()

            # Validate expected contents
            self.assertIn("name: (default values)", yaml_str)
            self.assertIn("name: model-a", yaml_str)
            # YAML may render booleans as "true" (lowercase) depending on the dumper
            self.assertTrue(("lazy: true" in yaml_str) or ("lazy: True" in yaml_str))
            # Ensure a blank line was added between list entries as the function post-processes
            self.assertIn("\n\n- name: model-a", yaml_str)
        finally:
            # Restore monkeypatched state
            if orig_dataclasses_fields is not None:
                dataclasses.fields = orig_dataclasses_fields
            if orig_model_settings is not None:
                mod.MODEL_SETTINGS = orig_model_settings
