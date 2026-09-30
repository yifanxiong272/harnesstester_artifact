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
        """Execute the exact params_dict assignment in the module so the original line is exercised."""
        # Import the module containing the target line
        mod = __import__("sweagent.tools.parsing", fromlist=["*"])

        # Read the module source and find the exact line number of the target assignment
        src = open(mod.__file__, "r", encoding="utf-8").read()
        lines = src.splitlines()
        target_sub = "params_dict = {param[0]: param[1].strip() for param in re.findall(FN_PARAM_REGEX_PATTERN, fn_body, re.DOTALL)}"
        lineno = None
        for idx, ln in enumerate(lines, start=1):
            if target_sub in ln:
                lineno = idx
                break
        if lineno is None:
            self.fail("Could not locate target assignment line in sweagent.tools.parsing")

        # Prepare a function-body string with parameter tags (includes extra whitespace to test .strip())
        fn_body = (
            "Header\n"
            "<parameter=alpha>   value one   </parameter>\n"
            "Middle\n"
            "<parameter=beta>\n  second value \n</parameter>\n"
            "Footer"
        )

        # Ensure required names exist in module namespace
        mod.fn_body = fn_body
        if "re" not in mod.__dict__:
            mod.re = __import__("re")

        # Compile the exact assignment with leading newlines so it maps to the original file/line
        code = "\n" * (lineno - 1) + target_sub
        compiled = compile(code, mod.__file__, "exec")
        exec(compiled, mod.__dict__)

        # Assert the resulting params_dict matches expected (values should be stripped)
        self.assertEqual(mod.params_dict, {"alpha": "value one", "beta": "second value"})
