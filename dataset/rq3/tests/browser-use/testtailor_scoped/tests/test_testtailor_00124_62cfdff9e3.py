import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.mcp.server')
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
        """Ensure get_parent_process_cmdline collects parent cmdlines up the chain."""
        # Build fake parent chain: current -> p1 -> p2 (empty cmdline) -> p3
        class FakeParent:
            def __init__(self, cmdline, parent):
                self._cmdline = cmdline
                self._parent = parent

            def cmdline(self):
                return self._cmdline

            def parent(self):
                return self._parent

        class FakeCurrent:
            def __init__(self, parent):
                self._parent = parent

            def parent(self):
                return self._parent

        class FakePsutilModule:
            class AccessDenied(Exception):
                pass

            class NoSuchProcess(Exception):
                pass

            def __init__(self, current):
                self._current = current

            def Process(self):
                return self._current

        p3 = FakeParent(['third', 'proc'], None)
        p2 = FakeParent([], p3)  # empty -> should be skipped
        p1 = FakeParent(['first', 'proc'], p2)
        current = FakeCurrent(parent=p1)
        fake_psutil = FakePsutilModule(current)

        # Patch the function's globals to use our fake psutil and ensure PSUTIL_AVAILABLE is True
        func_globals = get_parent_process_cmdline.__globals__
        orig_psutil = func_globals.get('psutil', None)
        orig_flag = func_globals.get('PSUTIL_AVAILABLE', None)
        func_globals['psutil'] = fake_psutil
        func_globals['PSUTIL_AVAILABLE'] = True

        try:
            result = get_parent_process_cmdline()
            expected = ' '.join(p1._cmdline) + ';' + ' '.join(p3._cmdline)
            self.assertEqual(result, expected)
        finally:
            # restore originals
            if orig_psutil is None:
                func_globals.pop('psutil', None)
            else:
                func_globals['psutil'] = orig_psutil

            if orig_flag is None:
                func_globals.pop('PSUTIL_AVAILABLE', None)
            else:
                func_globals['PSUTIL_AVAILABLE'] = orig_flag
