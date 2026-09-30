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
        """Trigger the branch where a config file contains a line starting with 'yes:'"""
        # Import needed modules at runtime to comply with "no top-level imports" rule
        tempfile = __import__("tempfile")
        io = __import__("io")
        contextlib = __import__("contextlib")
        os = __import__("os")

        tmp = None
        try:
            # Create a temporary file and write a line that, when stripped, starts with 'yes:'
            tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml")
            cfg_path = tmp.name
            tmp.write("some: value\n   yes: true\nother: no\n")
            tmp.close()

            # Capture stdout to inspect printed messages
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                result = check_config_files_for_yes([cfg_path])
            output = buf.getvalue()

            # The function should return True and print the expected messages including the filename
            self.assertTrue(result)
            self.assertIn("Configuration error detected.", output)
            self.assertIn("contains a line starting with 'yes:'", output)
            self.assertIn("replace 'yes:' with 'yes-always:'", output)
            self.assertIn(cfg_path, output)
        finally:
            if tmp is not None:
                try:
                    os.remove(cfg_path)
                except Exception:
                    pass
