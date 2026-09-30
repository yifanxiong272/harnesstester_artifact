import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.llm_provider.generic.base')
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
        """When the package spec is missing, _check_pkg should attempt to install the
        kebab-case package name and then import the original package name.
        """
        pkg = "my_package_name"
        pkg_kebab = "my-package-name"

        with patch("importlib.util.find_spec", return_value=None) as mock_find_spec, \
             patch("subprocess.check_call") as mock_check_call, \
             patch("importlib.import_module", return_value=object()) as mock_import_module:
            # Call the function under test
            _check_pkg(pkg)

            # verify we checked for the package spec
            mock_find_spec.assert_called_once_with(pkg)

            # verify pip was invoked with the kebab-case package name
            mock_check_call.assert_called_once_with(
                [sys.executable, "-m", "pip", "install", "-U", pkg_kebab]
            )

            # verify we attempted to import the original package name after install
            mock_import_module.assert_called_once_with(pkg)
