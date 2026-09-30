import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.bitbucket_provider')
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
        """_gef_filename should return diff.new.path when it is truthy."""
        class PathObj:
            def __init__(self, path):
                self.path = path

        class DiffObj:
            def __init__(self, new, old):
                self.new = new
                self.old = old

        diff = DiffObj(new=PathObj("src/module/file.py"), old=PathObj("old/module/file.py"))
        result = _gef_filename(diff)
        self.assertEqual(result, "src/module/file.py")
