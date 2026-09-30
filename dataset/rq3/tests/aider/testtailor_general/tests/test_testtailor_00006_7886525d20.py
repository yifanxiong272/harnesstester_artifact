import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.main')
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
        """Return False when none of the provided config files contain a line starting with 'yes:'"""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            existing = Path(tmpdir) / "config.yaml"
            # Write content that does not include a line that starts with 'yes:'
            existing.write_text("no: true\nsome_key: some_value\n# yes is mentioned but not as a key\n    maybe: yes\n")

            missing = Path(tmpdir) / "missing.yaml"  # this file does not exist

            result = check_config_files_for_yes([str(existing), str(missing)])
            self.assertFalse(result)
