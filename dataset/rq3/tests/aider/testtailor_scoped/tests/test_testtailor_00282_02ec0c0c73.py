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
        """sanity_check_model should print the Windows note when missing_keys and on Windows"""
        # Minimal dummy IO to capture outputs
        class DummyIO:
            def __init__(self):
                self.outputs = []
                self.warnings = []

            def tool_output(self, msg):
                self.outputs.append(msg)

            def tool_warning(self, msg):
                self.warnings.append(msg)

            def tool_error(self, msg):
                # not expected in this test, but provide implementation
                self.outputs.append(f"ERROR: {msg}")

            def confirm_ask(self, *args, **kwargs):
                return True

        io = DummyIO()

        # Minimal dummy model with the attributes used by sanity_check_model
        class DummyModel:
            def __init__(self):
                self.missing_keys = ["EXISTING_KEY", "MISSING_KEY"]
                self.keys_in_environment = True
                self.info = {"ctx": 1024}
                self.name = "test-model"

            def __str__(self):
                return "DummyModel(test-model)"

        model = DummyModel()

        # Set one environment variable and ensure the other is not set
        os.environ["EXISTING_KEY"] = "present"
        os.environ.pop("MISSING_KEY", None)

        expected_note = (
            "Note: You may need to restart your terminal or command prompt for `setx` to take"
            " effect."
        )

        # Patch platform.system globally to appear as Windows and stub out dependency checks.
        orig_platform_system = platform.system
        platform.system = lambda: "Windows"

        # Override check_for_dependencies in the module where sanity_check_model is defined
        mod_name = sanity_check_model.__module__
        mod = __import__(mod_name, fromlist=["*"])
        orig_check_deps = getattr(mod, "check_for_dependencies", None)
        setattr(mod, "check_for_dependencies", lambda io_arg, name_arg: None)

        try:
            show = sanity_check_model(io, model)
        finally:
            # Restore patched functions and environment cleanup
            platform.system = orig_platform_system
            if orig_check_deps is not None:
                setattr(mod, "check_for_dependencies", orig_check_deps)
            else:
                delattr(mod, "check_for_dependencies")

        # should return True because missing_keys is truthy
        self.assertTrue(show)

        # tool_warning should have been called to warn about expected env vars
        self.assertTrue(
            any(
                "Warning: DummyModel(test-model) expects these environment variables" in w
                for w in io.warnings
            ),
            f"Expected warning not found in {io.warnings}",
        )

        # tool_output should report both the Set and Not set statuses
        self.assertTrue(any(o == "- EXISTING_KEY: Set" for o in io.outputs), f"Outputs: {io.outputs}")
        self.assertTrue(any(o == "- MISSING_KEY: Not set" for o in io.outputs), f"Outputs: {io.outputs}")

        # And the Windows-specific note should be emitted
        self.assertTrue(any(o == expected_note for o in io.outputs), f"Outputs: {io.outputs}")

        # Clean up env
        os.environ.pop("EXISTING_KEY", None)
