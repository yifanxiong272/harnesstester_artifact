import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.log.ui.app')
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
        """Verify filter_log_folders returns only top-level directories as relative-like objects sorted by name."""
        # Create lightweight fake Path-like objects so the test doesn't rely on pathlib/tempfile imports.
        class RelFake:
            def __init__(self, name):
                self.name = name
            def __eq__(self, other):
                return getattr(other, "name", None) == self.name
            def __repr__(self):
                return f"RelFake({self.name!r})"

        class PathFake:
            def __init__(self, name, is_dir=True, children=None):
                self.name = name
                self._is_dir = is_dir
                # only relevant for directory entries that may have nested children
                self._children = children or []
            def iterdir(self):
                # emulate pathlib.Path.iterdir() returning Path-like entries
                return iter(self._children)
            def is_dir(self):
                return self._is_dir
            def relative_to(self, other):
                # return a relative-like object with a .name attribute
                return RelFake(self.name)
            def __repr__(self):
                return f"PathFake({self.name!r}, is_dir={self._is_dir})"

        # Build top-level children (out of order) and one file which should be ignored
        zeta = PathFake("zeta", is_dir=True)
        alpha_nested = PathFake("nested", is_dir=True)
        alpha = PathFake("alpha", is_dir=True, children=[alpha_nested])
        beta = PathFake("beta", is_dir=True)
        ignore_file = PathFake("ignore_me.txt", is_dir=False)

        main_log_path = PathFake("main", is_dir=True, children=[zeta, alpha, beta, ignore_file])

        result = filter_log_folders(main_log_path)

        expected = [RelFake("alpha"), RelFake("beta"), RelFake("zeta")]
        self.assertEqual(result, expected)
