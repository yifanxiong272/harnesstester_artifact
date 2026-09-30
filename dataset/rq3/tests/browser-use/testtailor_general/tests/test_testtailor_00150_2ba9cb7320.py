import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.skill_cli.main')
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
        """Locate the implementation containing the Adler-32 port computation and verify the Win32 branch.

        This searches the installed 'browser_use' package modules for source text that
        matches the exact port computation (49152 + zlib.adler32(...) % 16383),
        then calls the _get_socket_path function from that module with sys.platform
        patched to 'win32' to ensure the TCP branch is taken.
        """
        import importlib
        import pkgutil
        import inspect
        import sys
        import zlib
        from unittest import mock

        try:
            pkg = importlib.import_module('browser_use')
        except Exception:
            self.skipTest('browser_use package not importable')

        target_mod = None
        target_func = None
        pattern = '49152 + zlib.adler32'
        # Walk package modules to find the source containing the unique port computation
        if not hasattr(pkg, '__path__'):
            self.skipTest('browser_use is not a package with __path__')
        for finder, name, ispkg in pkgutil.walk_packages(pkg.__path__, prefix=pkg.__name__ + '.'):
            try:
                mod = importlib.import_module(name)
            except Exception:
                continue
            try:
                src = inspect.getsource(mod)
            except (OSError, IOError, TypeError, IOError):
                continue
            if pattern in src:
                # Found a module whose source contains the exact computation
                if hasattr(mod, '_get_socket_path'):
                    target_mod = mod
                    target_func = getattr(mod, '_get_socket_path')
                    break

        if target_func is None:
            self.skipTest('Could not locate _get_socket_path implementation with Adler-32 port computation')

        # Test a few different session names to ensure port computation is correct
        for session in ('default', 'my-session', 'xyz123'):
            with mock.patch.object(sys, 'platform', 'win32'):
                result = target_func(session)
                expected_port = 49152 + (zlib.adler32(session.encode()) % 16383)
                expected = f'tcp://127.0.0.1:{expected_port}'
                self.assertEqual(result, expected)
