import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.versioncheck')
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
        """Ensure install_from_main_branch delegates to utils.check_pip_install_extra with correct args."""
        func = globals().get("install_from_main_branch")
        self.assertIsNotNone(func, "install_from_main_branch must be available in globals()")

        class DummyUtils:
            def __init__(self):
                self.calls = []

            def check_pip_install_extra(self, io, arg2, prompt, packages, self_update=False):
                self.calls.append((io, arg2, prompt, packages, self_update))
                return "DUMMY_RESULT"

        dummy = DummyUtils()
        orig_utils = func.__globals__.get("utils", None)
        func.__globals__['utils'] = dummy
        try:
            fake_io = object()
            result = func(fake_io)

            # return value forwarded
            self.assertEqual(result, "DUMMY_RESULT")

            # one call recorded with exact expected arguments
            self.assertEqual(len(dummy.calls), 1)
            io_arg, arg2, prompt, packages, self_update = dummy.calls[0]
            self.assertIs(io_arg, fake_io)
            self.assertIsNone(arg2)
            self.assertEqual(prompt, "Install the development version of aider from the main branch?")
            self.assertEqual(packages, ["git+https://github.com/Aider-AI/aider.git"])
            self.assertTrue(self_update)
        finally:
            # restore original utils binding
            if orig_utils is not None:
                func.__globals__['utils'] = orig_utils
            else:
                del func.__globals__['utils']
