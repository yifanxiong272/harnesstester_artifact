import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.log.ui.utils')
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
        """Ensure get_script_time extracts timestamps from the first and last lines and returns the correct timedelta."""
        # Prepare a temporary file path in the current working directory
        content = (
            "INFO 2022-01-01 12:00:00+00:00 start\n"
            "some intermediate line that should be ignored\n"
            "INFO 2022-01-01 12:00:05+00:00 end\n"
        )

        stdout_path = Path.cwd() / f"tmp_{self._testMethodName}.log"
        try:
            # Write content to the file
            stdout_path.write_text(content)

            # Call the function under test
            result = get_script_time(stdout_path)

            # Expect a 5-second difference between the two timestamps
            expected = pd.Timedelta(seconds=5)
            self.assertEqual(result, expected)
        finally:
            try:
                stdout_path.unlink()
            except Exception:
                pass
