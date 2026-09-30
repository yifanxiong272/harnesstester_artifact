import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.utils')
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
        """Ensure show_messages calls dump when functions is truthy and prints formatted output."""
        messages = [{"role": "user", "content": "hello\nworld"}]
        functions = {"name": "my_func", "args": {"x": 1}}

        # Replace the dump function used by show_messages with a mock
        had_dump = "dump" in show_messages.__globals__
        original_dump = show_messages.__globals__.get("dump")
        mock_dump = unittest.mock.Mock()
        show_messages.__globals__["dump"] = mock_dump

        try:
            # Patch builtins.print to capture printed output without needing io
            with unittest.mock.patch("builtins.print") as mock_print:
                show_messages(messages, title="Info", functions=functions)

                # Ensure print was called and capture the printed value
                mock_print.assert_called_once()
                printed = mock_print.call_args[0][0]

            # The formatted output should include the title and the message lines
            self.assertIn("INFO", printed)
            self.assertIn("USER hello", printed)
            self.assertIn("USER world", printed)

            # dump should have been called once with the functions argument
            mock_dump.assert_called_once_with(functions)
        finally:
            # Restore original dump to avoid side effects on other tests
            if had_dump:
                show_messages.__globals__["dump"] = original_dump
            else:
                # remove the key we added
                del show_messages.__globals__["dump"]
