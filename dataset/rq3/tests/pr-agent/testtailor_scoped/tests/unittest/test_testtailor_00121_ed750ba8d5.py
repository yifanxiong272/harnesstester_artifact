import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.algo.language_handler')
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
        """Ensure get_settings().bad_extensions.extra is appended when bad_extensions is falsy
        and use_extra_bad_extensions is True.
        """
        # Build a minimal settings object with the attributes the function expects
        class _S: 
            pass

        settings = _S()
        settings.bad_extensions = _S()
        settings.bad_extensions.default = ['exe', 'dll']
        settings.bad_extensions.extra = ['map', 'lock']
        settings.config = _S()
        settings.config.use_extra_bad_extensions = True

        # Patch the get_settings used inside the module where is_valid_file is defined
        with patch(f"{is_valid_file.__module__}.get_settings", return_value=settings):
            # 'foo.map' should be considered invalid because 'map' comes from extra and is appended
            self.assertFalse(is_valid_file("some/path/foo.map", bad_extensions=None))
            # 'bar.txt' should be valid because 'txt' is not in default nor extra
            self.assertTrue(is_valid_file("some/path/bar.txt", bad_extensions=None))
