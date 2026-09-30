import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.tools.utils')
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
        """Ensure that when there is text before a multiline (heredoc) command, the function
        finds the match and preserves the pre_action and the multiline block.
        """
        action = "echo before\ncat << 'EOF'\nline1\nline2\nEOF\nafter\n"

        # match_fct must return a re.Match with group(3) being the EOF marker name.
        # Pattern groups:
        # 1: the whole matched block (from 'cat' through the closing EOF line)
        # 2: the heredoc opener part (<< 'EOF'\n)
        # 3: the EOF token (EOF)
        def match_fct(s: str):
            return re.search(r"(?ms)(cat[^\n]*(<<\s*'([^']+)'\n).*?\n\3\n)", s)

        result = _guard_multiline_input(action, match_fct)

        # pre_action should be preserved
        self.assertIn("echo before", result)
        # the multiline command opener should be present and include the EOF marker
        self.assertIn("cat << 'EOF'", result)
        # the contents and the closing EOF should be preserved
        self.assertIn("line1", result)
        self.assertIn("line2", result)
        self.assertIn("EOF", result)
