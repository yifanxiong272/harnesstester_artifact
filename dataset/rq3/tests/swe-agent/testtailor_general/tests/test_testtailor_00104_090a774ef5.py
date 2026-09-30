import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.tools.parsing')
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
        """Find a parse function implementation that uses FN_REGEX_PATTERN and exercise it.

        The goal is to trigger the code path that runs:
            fn_match = re.search(FN_REGEX_PATTERN, model_response["message"], re.DOTALL)

        We import the parsing module dynamically, locate a concrete subclass of AbstractParseFunction
        whose source contains FN_REGEX_PATTERN and re.search, instantiate it, and call it with a
        model_response whose "message" matches the regex pattern. We pass a Command with the matching
        name so the parser does not raise a FormatError for a missing command.
        """
        importlib = __import__("importlib")
        inspect = __import__("inspect")
        parsing = importlib.import_module("sweagent.tools.parsing")
        commands_mod = importlib.import_module("sweagent.tools.commands")

        # Find a concrete parser class referencing the FN_REGEX_PATTERN and re.search
        found_parser = None
        for name, obj in vars(parsing).items():
            if not inspect.isclass(obj):
                continue
            if not issubclass(obj, parsing.AbstractParseFunction) or obj is parsing.AbstractParseFunction:
                continue
            try:
                src = inspect.getsource(obj)
            except (OSError, TypeError):
                continue
            if "FN_REGEX_PATTERN" in src and "re.search" in src:
                try:
                    parser_inst = obj()
                except Exception:
                    # Can't instantiate this parser without args - skip
                    continue
                found_parser = parser_inst
                break

        if found_parser is None:
            self.skipTest("No suitable parser class referencing FN_REGEX_PATTERN was found")

        # Create a Command with the expected name so parsing can locate it
        Command = getattr(commands_mod, "Command")
        cmd = Command(name="test_fn", docstring="a test function command")

        # pattern expects: <function=NAME>\nCONTENT</function>
        model_response = {"message": "<function=test_fn>\nline1\nline2</function>"}

        # Call the parser with the command present so no FormatError is raised
        result = found_parser(model_response, [cmd])

        # Validate that the parser returned the expected shape (tuple of two strings)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(isinstance(x, str) for x in result))
