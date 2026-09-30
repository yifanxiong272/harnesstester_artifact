import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.versioncheck')
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
        """When a recent VERSION_CHECK_FNAME exists, check_version returns early and logs a 'Too soon' message."""
        # Ensure the version check cache file exists and has a recent mtime (< 1 day)
        VERSION_CHECK_FNAME.parent.mkdir(parents=True, exist_ok=True)
        try:
            # create/touch the file and set its modification time to ~1 hour ago
            VERSION_CHECK_FNAME.touch(exist_ok=True)
            now = time.time()
            one_hour = 60 * 60
            mtime = now - one_hour
            os.utime(VERSION_CHECK_FNAME, (mtime, mtime))

            class FakeIO:
                def __init__(self):
                    self.outputs = []
                    self.errors = []
                    self.warnings = []

                def tool_output(self, msg):
                    self.outputs.append(msg)

                def tool_error(self, msg):
                    self.errors.append(msg)

                def tool_warning(self, msg):
                    self.warnings.append(msg)

            io = FakeIO()

            # Call with verbose True so it will emit the "Too soon to check version" message
            result = check_version(io, just_check=False, verbose=True)

            # Because the file is recent (< day), the function should return early (None)
            self.assertIsNone(result)

            # And the Too soon message should have been emitted
            joined = "\n".join(io.outputs)
            self.assertIn("Too soon to check version", joined)
            self.assertIn("hours", joined)
        finally:
            # Clean up the file we created
            try:
                VERSION_CHECK_FNAME.unlink()
            except Exception:
                pass
