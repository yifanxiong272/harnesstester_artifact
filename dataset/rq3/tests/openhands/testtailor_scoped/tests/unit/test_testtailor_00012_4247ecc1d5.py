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
        """Verify grep_to_cmdrun correctly quotes the pattern, path and include and
        constructs the expected ripgrep command string (with echo header and head limiter).
        """
        # Complex pattern and path with spaces/shell-special chars to ensure quoting is used
        pattern = "foo 'bar' $(rm -rf /)"
        path = "/some path/with spaces"
        include = "*.py"

        # Call the function under test
        actual = grep_to_cmdrun(pattern=pattern, path=path, include=include)

        # Build expected string using shlex.quote so we match the implementation's quoting
        expected_quoted_pattern = shlex.quote(pattern)
        expected_path_arg = shlex.quote(path)
        expected_quoted_include = shlex.quote(include)

        rg_cmd = f'rg -li {expected_quoted_pattern} --sortr=modified'
        rg_cmd += f' --glob {expected_quoted_include}'
        complete_cmd = f'{rg_cmd} {expected_path_arg} | head -n 100'
        expected_echo = f'echo "Below are the execution results of the search command: {complete_cmd}\n"; '
        expected = expected_echo + complete_cmd

        self.assertEqual(actual, expected)

        # Also test the default path (None -> '.') and no include provided
        pattern2 = "simple-pattern"
        actual2 = grep_to_cmdrun(pattern=pattern2, path=None, include=None)

        expected_quoted_pattern2 = shlex.quote(pattern2)
        expected_path_arg2 = '.'  # default when path is None
        rg_cmd2 = f'rg -li {expected_quoted_pattern2} --sortr=modified'
        complete_cmd2 = f'{rg_cmd2} {expected_path_arg2} | head -n 100'
        expected_echo2 = f'echo "Below are the execution results of the search command: {complete_cmd2}\n"; '
        expected2 = expected_echo2 + complete_cmd2

        self.assertEqual(actual2, expected2)
