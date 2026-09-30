import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.data_science.ensemble.test')
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
        """Locate the module that defines load_ensemble_spec, stub the file read for the expected spec path,
        and verify load_ensemble_spec returns the stubbed content."""
        # discover the source file that contains the target function
        from pathlib import Path
        import importlib.util
        import sys
        import io
        import builtins
        import os
        from unittest import mock

        cwd = Path.cwd()
        candidate = None
        for p in cwd.rglob("*.py"):
            try:
                text = p.read_text(encoding="utf-8")
            except Exception:
                continue
            if "def load_ensemble_spec(" in text:
                candidate = p
                break

        self.assertIsNotNone(candidate, "Could not find a python file defining load_ensemble_spec in the repo")

        # load the module from the discovered file
        spec_name = f"test_module_{abs(hash(str(candidate))) % (10**8)}"
        spec = importlib.util.spec_from_file_location(spec_name, str(candidate))
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec_name] = module
        spec.loader.exec_module(module)

        # ensure the function and COMPETITION_PATH exist
        self.assertTrue(hasattr(module, "load_ensemble_spec"), "Module does not have load_ensemble_spec")
        self.assertTrue(hasattr(module, "COMPETITION_PATH"), "Module does not have COMPETITION_PATH")

        expected_path = str(module.COMPETITION_PATH / "spec" / "ensemble.md")

        real_open = builtins.open

        def fake_open(file, mode="r", *args, **kwargs):
            # match the exact expected path or a path that endswith spec/ensemble.md under the competition folder
            try:
                file_str = str(file)
            except Exception:
                file_str = file
            if file_str == expected_path or (
                file_str.endswith(os.path.join("spec", "ensemble.md"))
                and "aerial-cactus-identification" in file_str
            ):
                return io.StringIO("fake-ensemble-content")
            return real_open(file, mode, *args, **kwargs)

        with mock.patch("builtins.open", new=fake_open):
            content = module.load_ensemble_spec()
        self.assertEqual(content, "fake-ensemble-content")
