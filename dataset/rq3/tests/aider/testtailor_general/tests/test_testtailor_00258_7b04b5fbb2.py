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
        """complete the test case here"""
        fake_io = unittest.mock.Mock()

        # ensure we don't take the Docker-image early-return path
        func_globals = install_upgrade.__globals__
        os_mod = func_globals["os"]
        if "AIDER_DOCKER_IMAGE" in os_mod.environ:
            del os_mod.environ["AIDER_DOCKER_IMAGE"]

        utils_obj = func_globals["utils"]

        latest = "2.0.0"
        expected_new_ver_text = f"Newer aider version v{latest} is available."

        with unittest.mock.patch.object(utils_obj, "check_pip_install_extra", return_value=True) as mock_check:
            with self.assertRaises(SystemExit):
                install_upgrade(fake_io, latest_version=latest)

        # verify output was emitted before exit
        fake_io.tool_output.assert_called_once_with("Re-run aider to use new version.")
        # verify we called the pip check with the expected arguments
        mock_check.assert_called_once_with(
            fake_io,
            None,
            expected_new_ver_text,
            ["aider-chat"],
            self_update=True,
        )
