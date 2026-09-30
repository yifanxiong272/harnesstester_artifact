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
        """When no latest_version is provided and not running in Docker, ensure the prompt text is the generic install message."""
        # Ensure no Docker image is set in the environment
        if "AIDER_DOCKER_IMAGE" in os.environ:
            del os.environ["AIDER_DOCKER_IMAGE"]

        captured = {}

        def fake_check_pip_install_extra(io_arg, none_arg, text_arg, pkg_list, self_update=False):
            # capture arguments for assertions
            captured['io'] = io_arg
            captured['none_arg'] = none_arg
            captured['text'] = text_arg
            captured['pkg_list'] = pkg_list
            captured['self_update'] = self_update
            # return False to avoid sys.exit path
            return False

        # Simple IO substitute
        class DummyIO:
            def __init__(self):
                self.outputs = []
                self.warnings = []
            def tool_output(self, msg):
                self.outputs.append(msg)
            def tool_warning(self, msg):
                self.warnings.append(msg)

        io_obj = DummyIO()

        # Ensure we can patch or temporarily set the attribute even if it does not exist
        sentinel = object()
        original = getattr(utils, "check_pip_install_extra", sentinel)
        try:
            setattr(utils, "check_pip_install_extra", fake_check_pip_install_extra)
            result = install_upgrade(io_obj)  # latest_version omitted -> should use generic text
        finally:
            # restore original state
            if original is sentinel:
                try:
                    delattr(utils, "check_pip_install_extra")
                except Exception:
                    pass
            else:
                setattr(utils, "check_pip_install_extra", original)

        # Function should return None when check_pip_install_extra returns False
        self.assertIsNone(result)
        # Verify the prompt text used when latest_version is not provided
        self.assertEqual(captured.get('text'), "Install latest version of aider?")
        # Verify packages and flag passed through
        self.assertEqual(captured.get('pkg_list'), ["aider-chat"])
        self.assertTrue(captured.get('self_update'))
