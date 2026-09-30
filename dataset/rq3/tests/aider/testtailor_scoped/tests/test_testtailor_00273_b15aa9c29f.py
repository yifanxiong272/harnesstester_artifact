import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.analytics')
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
        """Ensure save_data handles OSError when writing analytics file by disabling analytics and not raising."""
        # Create a fake home directory inside the current working directory
        fake_home = Path.cwd() / "fake_home_for_test"
        fake_home.mkdir(parents=True, exist_ok=True)

        analytics_path = fake_home / ".aider" / "analytics.json"

        # Create a fake Path-like object that simulates an OSError when write_text is called
        class FakePath:
            def __init__(self, p):
                self._p = Path(p)
                self.name = self._p.name
                self.parent = self._p.parent

            def exists(self):
                # Simulate that the analytics file does not exist yet
                return False

            def write_text(self, data):
                # Simulate a failure when attempting to write the analytics file
                raise OSError("simulated write failure")

        fake_path = FakePath(analytics_path)

        # Patch Path.home so Analytics doesn't touch the real home, and patch
        # Analytics.get_data_file_path to return our FakePath which raises on write.
        with patch("pathlib.Path.home", return_value=fake_home):
            with patch.object(Analytics, "get_data_file_path", return_value=fake_path):
                # Instantiating Analytics will call get_or_create_uuid -> save_data,
                # and our FakePath.write_text will raise OSError, hitting the except branch.
                a = Analytics()

                # A user_id should still have been generated before the failed save
                self.assertIsNotNone(a.user_id)

                # The analytics file should not exist because the write failed
                self.assertFalse(analytics_path.exists())

                # Analytics providers should be disabled (mp/ph None) as disable() is called
                self.assertIsNone(a.mp)
                self.assertIsNone(a.ph)
