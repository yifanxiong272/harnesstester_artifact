import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.data_science.conf')
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
        """Ensure get_ds_env accepts a valid conf_type and applies provided settings without actually invoking Docker."""
        # Monkeypatch DockerEnv.prepare to avoid real docker operations
        original_prepare = DockerEnv.prepare
        try:
            prepared_called = {"ok": False}

            def fake_prepare(self):
                # mark that prepare was called and do nothing else
                prepared_called["ok"] = True

            DockerEnv.prepare = fake_prepare

            # Call function under test with a valid conf_type and custom settings
            extra_vols = {"/host/path": "/container/path"}
            env = get_ds_env(conf_type="kaggle", extra_volumes=extra_vols, running_timeout_period=123, enable_cache=False)

            # verify prepare was invoked (our fake)
            self.assertTrue(prepared_called["ok"], "DockerEnv.prepare should be called")

            # verify the returned env has the expected configuration applied
            self.assertTrue(hasattr(env, "conf"))
            self.assertEqual(env.conf.extra_volumes, extra_vols)
            self.assertEqual(env.conf.running_timeout_period, 123)
            # enable_cache should be set because we passed a non-None value
            self.assertEqual(env.conf.enable_cache, False)

            # verify this is the DS docker config by checking fields specific to DSDockerConf
            self.assertEqual(getattr(env.conf, "image", None), "local_ds:latest")
            self.assertEqual(getattr(env.conf, "mount_path", None), "/kaggle/workspace")
            self.assertEqual(getattr(env.conf, "default_entry", None), "python main.py")
        finally:
            # restore original method
            DockerEnv.prepare = original_prepare
