import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.scrape')
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
        """When installing Playwright, if the chromium install fails, io.tool_error is called and function returns."""
        # Find the module that defines install_playwright
        import sys
        from types import SimpleNamespace

        mod = None
        for m in list(sys.modules.values()):
            if m is None:
                continue
            if getattr(m, "install_playwright", None) is not None:
                mod = m
                break
        self.assertIsNotNone(mod, "Could not find module containing install_playwright")

        # Prepare a fake io with the expected methods
        io = MagicMock()
        io.tool_output = MagicMock()
        io.confirm_ask = MagicMock(return_value=True)
        io.tool_error = MagicMock()

        # Prepare a fake utils with the expected behaviors:
        # - get_pip_install returns a pip command list (won't be run because has_pip=True)
        # - run_install for chromium returns failure to trigger io.tool_error branch
        mock_utils = MagicMock()
        mock_utils.get_pip_install.return_value = ["pip", "install", "aider-chat[playwright]"]
        mock_utils.run_install.return_value = (False, "chromium install failed")

        # Patch the module-level dependencies (check_env, utils, urls) on the found module
        with patch.object(mod, "check_env", return_value=(True, False)), \
             patch.object(mod, "utils", new=mock_utils), \
             patch.object(mod, "urls", new=SimpleNamespace(enable_playwright="http://example.com")):
            result = mod.install_playwright(io)

        # The function should have reported the error via io.tool_error and returned None
        io.tool_error.assert_called_once_with("chromium install failed")
        self.assertIsNone(result)
