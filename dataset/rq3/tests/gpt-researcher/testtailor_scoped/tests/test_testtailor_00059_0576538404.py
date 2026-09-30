import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('multi_agents.agents.utils.views')
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
        """capture printed output by temporarily replacing the built-in print"""
        parts = []

        def fake_print(*args, sep=' ', end='\n', file=None, flush=False):
            parts.append(sep.join(str(a) for a in args) + end)

        builtins_ns = __builtins__
        is_dict = isinstance(builtins_ns, dict)
        if is_dict:
            orig_print = builtins_ns.get('print')
            builtins_ns['print'] = fake_print
        else:
            orig_print = getattr(builtins_ns, 'print')
            setattr(builtins_ns, 'print', fake_print)

        try:
            # call without specifying agent to use the default "RESEARCHER"
            print_agent_output("hello world")
        finally:
            if is_dict:
                builtins_ns['print'] = orig_print
            else:
                setattr(builtins_ns, 'print', orig_print)

        output = "".join(parts)
        expected_line_start = f"{AgentColor.RESEARCHER.value}RESEARCHER: hello world"
        self.assertIn(expected_line_start, output)
        self.assertTrue(output.endswith(f"{Style.RESET_ALL}\n"))
