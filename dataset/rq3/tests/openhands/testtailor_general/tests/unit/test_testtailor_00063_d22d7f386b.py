import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.agenthub.readonly_agent.function_calling')
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
        """Verify grep_to_cmdrun properly quotes pattern, path, and include and builds the rg command."""
        import shlex
        import importlib
        import pkgutil
        import unittest

        # Try to find grep_to_cmdrun in the expected module, its submodules, or elsewhere in the package.
        func = None
        try:
            base_mod = importlib.import_module('openhands.agenthub.readonly_agent.tools')
            func = getattr(base_mod, 'grep_to_cmdrun', None)
            if func is None:
                # Search submodules of the tools module
                if hasattr(base_mod, '__path__'):
                    for _finder, name, _ispkg in pkgutil.walk_packages(base_mod.__path__, base_mod.__name__ + "."):
                        sub = importlib.import_module(name)
                        if hasattr(sub, 'grep_to_cmdrun'):
                            func = getattr(sub, 'grep_to_cmdrun')
                            break
        except Exception:
            # If import failed, we'll try to search the whole openhands package
            func = None

        if func is None:
            # Attempt to search the entire openhands package for the function
            try:
                pkg = importlib.import_module('openhands')
                if hasattr(pkg, '__path__'):
                    for _finder, name, _ispkg in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
                        sub = importlib.import_module(name)
                        if hasattr(sub, 'grep_to_cmdrun'):
                            func = getattr(sub, 'grep_to_cmdrun')
                            break
            except Exception:
                func = None

        if func is None:
            # If we still can't find it, skip the test to avoid a false failure.
            raise unittest.SkipTest("grep_to_cmdrun not found in project modules")

        # Simple pattern, default path (should use '.')
        pattern_simple = "simple-pattern"
        cmd_simple = func(pattern_simple)
        expected_quoted_pattern_simple = shlex.quote(pattern_simple)
        self.assertIn(expected_quoted_pattern_simple, cmd_simple)
        self.assertIn('rg -li', cmd_simple)
        self.assertIn('--sortr=modified', cmd_simple)
        self.assertIn('| head -n 100', cmd_simple)
        # Default path should include '.' (may be adjacent to other tokens)
        self.assertIn('.', cmd_simple)

        # Complex pattern and path with special shell characters to ensure proper quoting
        pattern_complex = "complex pattern$with'quotes\" and spaces"
        path_complex = "/some path/with $pecial'chars"
        include_pattern = "*.py"
        cmd_complex = func(pattern_complex, path_complex, include_pattern)

        expected_quoted_pattern = shlex.quote(pattern_complex)
        expected_quoted_path = shlex.quote(path_complex)
        expected_quoted_include = shlex.quote(include_pattern)

        # Ensure quoting applied to pattern, path and include
        self.assertIn(expected_quoted_pattern, cmd_complex)
        self.assertIn(f'--glob {expected_quoted_include}', cmd_complex)
        self.assertIn(expected_quoted_path, cmd_complex)

        # Ensure echo header contains the composed command and prefix is present
        expected_prefix = 'echo "Below are the execution results of the search command: '
        self.assertTrue(cmd_complex.startswith(expected_prefix))
        self.assertIn('| head -n 100', cmd_complex)
        # Ensure rg flags are present
        self.assertIn('rg -li', cmd_complex)
        self.assertIn('--sortr=modified', cmd_complex)
