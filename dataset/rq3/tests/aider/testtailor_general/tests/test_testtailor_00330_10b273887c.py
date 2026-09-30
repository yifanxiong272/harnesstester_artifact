import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.args')
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
        """Invoke main with 'completion' and a shell argument so the branch assigning
        shell = sys.argv[2] is executed and shtab.complete is invoked with the parser
        and shell name.
        """
        argv = ["aider", "completion", "bash"]

        with patch("aider.main.shtab.SUPPORTED_SHELLS", new=["bash", "zsh"]), \
             patch("aider.main.shtab.complete", return_value="COMPLETION_SCRIPT") as mock_complete, \
             patch.object(sys, "argv", argv), \
             patch("builtins.print") as mock_print:
            # Call the main function which should follow the 'completion' branch
            main()

            # Ensure shtab.complete was invoked exactly once
            mock_complete.assert_called_once()

            # Inspect the call to shtab.complete to verify arguments
            args, kwargs = mock_complete.call_args
            # First positional arg should be the parser created by get_parser
            self.assertTrue(args, "Expected a parser positional argument to shtab.complete")
            parser_passed = args[0]
            # The parser.prog should have been set to "aider" by the main() logic
            self.assertEqual(getattr(parser_passed, "prog", None), "aider")
            # The shell keyword argument should be the third argv element ("bash")
            self.assertEqual(kwargs.get("shell"), "bash")
