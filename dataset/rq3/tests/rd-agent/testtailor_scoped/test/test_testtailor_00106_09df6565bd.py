import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.app.utils.ws')
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
        """complete the test case here"""
        import rdagent.app.utils.ws as ws
        from unittest.mock import patch, MagicMock

        # Prepare fake DS_RD_SETTING so the data_path branch is exercised
        fake_setting = MagicMock()
        fake_setting.local_data_path = "/tmp/data"
        fake_setting.sample_data_by_LLM = True

        # Prepare fake T(...) that returns an object whose r() returns the target path
        fake_T = MagicMock()
        fake_T.return_value.r.return_value = "/mnt/input"

        # Capture what get_ds_env receives and return a fake env
        captured = {}

        def fake_get_ds_env(*args, extra_volumes=None, running_timeout_period=None, enable_cache=None, **kwargs):
            captured["extra_volumes"] = extra_volumes
            captured["running_timeout_period"] = running_timeout_period
            captured["enable_cache"] = enable_cache
            env = MagicMock()
            env.conf = MagicMock()
            env.run = MagicMock()
            return env

        with patch.object(ws, "DS_RD_SETTING", fake_setting):
            with patch.object(ws, "T", fake_T):
                with patch.object(ws, "get_ds_env", side_effect=fake_get_ds_env) as mocked_get:
                    # Call the function under test
                    ws.run("comp1", "echo hi", local_path="/work", mount_path="/mnt")

                    # Validate extra_volumes constructed as expected
                    expected_data_path = "/tmp/data/comp1"  # because sample_data_by_LLM is True
                    expected_target = "/mnt/input"
                    self.assertIn(expected_data_path, captured["extra_volumes"])
                    self.assertEqual(captured["extra_volumes"][expected_data_path], expected_target)

                    # Validate get_ds_env received the specific runtime flags
                    self.assertEqual(captured["running_timeout_period"], None)
                    self.assertEqual(captured["enable_cache"], False)
                    mocked_get.assert_called()
