import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.skill_cli.utils')
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
        """Ensure is_process_alive uses OpenProcess on Windows and returns True on a non-zero handle."""
        import sys
        import importlib
        import pkgutil
        import inspect
        import ctypes
        from unittest import mock

        # Import the package
        try:
            import browser_use
        except Exception as exc:
            self.fail(f"Could not import browser_use package: {exc}")

        target_func = None

        # Check if the function is at package level
        if hasattr(browser_use, 'is_process_alive') and inspect.isfunction(getattr(browser_use, 'is_process_alive')):
            target_func = getattr(browser_use, 'is_process_alive')
        else:
            # Walk submodules to find is_process_alive
            if hasattr(browser_use, '__path__'):
                for finder, name, ispkg in pkgutil.walk_packages(browser_use.__path__, browser_use.__name__ + '.'):
                    try:
                        mod = importlib.import_module(name)
                    except Exception:
                        continue
                    if hasattr(mod, 'is_process_alive') and inspect.isfunction(getattr(mod, 'is_process_alive')):
                        target_func = getattr(mod, 'is_process_alive')
                        break

        assert target_func is not None, "Could not find is_process_alive in browser_use package"

        orig_platform = sys.platform
        try:
            # Force Windows branch
            sys.platform = 'win32'

            # Dummy kernel32 implementation
            class DummyKernel32:
                def __init__(self):
                    self.open_called = False
                    self.close_called = False
                    self.open_args = None
                    self.closed_handle = None

                def OpenProcess(self, flags, inherit, pid):
                    self.open_called = True
                    self.open_args = (flags, inherit, pid)
                    return 0xBEEF  # non-zero handle indicates success

                def CloseHandle(self, handle):
                    self.close_called = True
                    self.closed_handle = handle
                    return True

            dummy_kernel32 = DummyKernel32()
            # Create the windll object that contains kernel32
            dummy_windll = mock.MagicMock()
            dummy_windll.kernel32 = dummy_kernel32

            # Patch ctypes.windll (create if missing) so the function uses our dummy
            with mock.patch('ctypes.windll', new=dummy_windll, create=True):
                alive = target_func(12345)

            # Verify behavior
            self.assertTrue(alive)
            self.assertTrue(dummy_kernel32.open_called)
            self.assertEqual(dummy_kernel32.open_args[2], 12345)
            self.assertTrue(dummy_kernel32.close_called)
            self.assertEqual(dummy_kernel32.closed_handle, 0xBEEF)
        finally:
            sys.platform = orig_platform
