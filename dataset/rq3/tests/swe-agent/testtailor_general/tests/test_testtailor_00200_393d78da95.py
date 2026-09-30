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
        """Ensure that when the matched multiline command already has the proper heredoc
        marker on its first line, the original match_action is appended unchanged
        (exercise the parsed_action.append(match_action) branch).
        """
        action = (
            "pre_line\n"
            "cat > /tmp/file << 'MYEOF'\n"
            "line1\n"
            "line2\n"
            "MYEOF\n"
            "post_line"
        )

        def match_fct(s: str):
            start_marker = "cat > /tmp/file << 'MYEOF'"
            start = s.find(start_marker)
            if start == -1:
                return None
            # find the closing marker (end of the matched block)
            end_marker = "\nMYEOF"
            end_idx = s.find(end_marker, start)
            if end_idx == -1:
                return None
            end = end_idx + len(end_marker)

            class DummyMatch:
                def __init__(self, st, ed, eof):
                    self._st = st
                    self._ed = ed
                    self._eof = eof

                def start(self):
                    return self._st

                def end(self):
                    return self._ed

                def group(self, idx):
                    if idx == 3:
                        return self._eof
                    raise IndexError("Only group(3) supported in DummyMatch")

            return DummyMatch(start, end, "MYEOF")

        result = _guard_multiline_input(action, match_fct)

        # The matched first line should be present and unchanged.
        self.assertIn("cat > /tmp/file << 'MYEOF'", result)
        # There should be exactly one occurrence of the heredoc suffix (i.e., it wasn't added twice).
        self.assertEqual(result.count("<< 'MYEOF'"), 1)
        # The EOF marker should still be present
        self.assertIn("MYEOF", result)
