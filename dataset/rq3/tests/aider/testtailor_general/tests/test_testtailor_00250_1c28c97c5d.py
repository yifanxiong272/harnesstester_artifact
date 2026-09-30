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
        """Call show_messages with a non-empty functions arg so dump(functions) is executed."""
        messages = [{"role": "user", "content": "hello"}]
        functions = [{"name": "foo"}]

        # Capture all prints by temporarily replacing builtins.print
        captured = []

        def fake_print(*args, **kwargs):
            sep = kwargs.get("sep", " ")
            end = kwargs.get("end", "\n")
            s = sep.join(str(a) for a in args) + end
            captured.append(s)
            return orig_print(*args, **kwargs)

        # Support both dict and module forms of __builtins__
        if isinstance(__builtins__, dict):
            orig_print = __builtins__.get("print")
            __builtins__["print"] = fake_print
        else:
            orig_print = __builtins__.print
            __builtins__.print = fake_print

        try:
            show_messages(messages, title="greeting", functions=functions)
        finally:
            # Restore original print
            if isinstance(__builtins__, dict):
                __builtins__["print"] = orig_print
            else:
                __builtins__.print = orig_print

        out = "".join(captured)
        # Ensure the formatted message was printed
        self.assertIn("GREETING", out)
        self.assertIn("USER hello", out)
        # Ensure dump was invoked and printed the functions value in some form
        self.assertIn("functions:", out)
        # The dumped representation is pretty-printed, so check for keys and values
        self.assertIn('"name"', out)  # key present
        self.assertIn("foo", out)     # value present
