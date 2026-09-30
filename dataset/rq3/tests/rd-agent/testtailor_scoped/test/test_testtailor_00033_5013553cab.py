import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.data_science.proposal.exp_gen.select.expand')
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
        """Find the source file that defines LatestCKPSelector, load it, instantiate it,
        and assert that its __init__ logs the expected message."""
        import importlib.util
        import importlib
        import sys
        from pathlib import Path

        # Try to locate the rdagent package directory by walking up from this test file
        current = Path(__file__).resolve()
        rdagent_dir = None
        for ancestor in current.parents:
            candidate = ancestor / "rdagent"
            if candidate.is_dir():
                rdagent_dir = candidate
                break

        # Fallback: try importing rdagent package and use its location
        if rdagent_dir is None:
            try:
                pkg = importlib.import_module("rdagent")
                rdagent_dir = Path(getattr(pkg, "__file__")).resolve().parent
            except Exception:
                rdagent_dir = None

        self.assertIsNotNone(rdagent_dir, "Could not locate rdagent package directory to search for source files")

        # Search for the file that contains the LatestCKPSelector class definition
        target_path = None
        for py_file in rdagent_dir.rglob("*.py"):
            try:
                text = py_file.read_text(encoding="utf-8")
            except Exception:
                continue
            if "class LatestCKPSelector" in text:
                target_path = py_file
                break

        self.assertIsNotNone(
            target_path, f"Could not find source file defining LatestCKPSelector under {rdagent_dir}"
        )

        # Load the module from the discovered file under a unique temporary name
        module_name = f"test_loaded_{target_path.stem}_{abs(hash(str(target_path))) % 100000}"
        spec = importlib.util.spec_from_file_location(module_name, str(target_path))
        self.assertIsNotNone(spec, "Failed to create import spec for the target module")
        mod = importlib.util.module_from_spec(spec)
        loader = spec.loader
        self.assertIsNotNone(loader, "Spec.loader is None for the target module")
        # Execute the module to populate attributes (this runs top-level code)
        loader.exec_module(mod)
        # Put it into sys.modules so that relative imports inside it may behave more normally
        sys.modules[module_name] = mod

        self.assertTrue(hasattr(mod, "LatestCKPSelector"), "Loaded module does not define LatestCKPSelector")
        LatestCKPSelector = getattr(mod, "LatestCKPSelector")

        # Capture logger.info calls by replacing/setting module logger with dummy logger
        messages = []

        class DummyLogger:
            def info(self, msg):
                messages.append(msg)

        orig_logger = getattr(mod, "logger", None)
        try:
            setattr(mod, "logger", DummyLogger())
            # Instantiation should trigger the logger.info call in __init__
            LatestCKPSelector()
            # Assert that expected message was logged
            self.assertTrue(
                any("Using latest selector by default" in str(m) for m in messages),
                f"Expected log message not found in messages: {messages}",
            )
        finally:
            # Restore original logger to avoid side effects
            if orig_logger is not None:
                setattr(mod, "logger", orig_logger)
            else:
                # remove attribute if originally absent
                try:
                    delattr(mod, "logger")
                except Exception:
                    pass
