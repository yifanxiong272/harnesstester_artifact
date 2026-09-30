import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.server.file_config')
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
        """Test sanitize_filename: removes path components, filters chars, and truncates long names."""
        import importlib
        import pkgutil

        # Try common candidate modules first, then scan openhands.server submodules if needed
        candidates = [
            'openhands.server.file_config',
            'openhands.server.file_utils',
            'openhands.server.utils',
            'openhands.server.shared',
            'openhands.server.files',
        ]
        sanitize = None
        for modname in candidates:
            try:
                mod = importlib.import_module(modname)
            except Exception:
                continue
            if hasattr(mod, 'sanitize_filename'):
                sanitize = getattr(mod, 'sanitize_filename')
                break

        if sanitize is None:
            # Scan submodules of openhands.server
            try:
                srv = importlib.import_module('openhands.server')
                for finder, name, ispkg in pkgutil.iter_modules(srv.__path__):
                    try:
                        mod = importlib.import_module('openhands.server.' + name)
                    except Exception:
                        continue
                    if hasattr(mod, 'sanitize_filename'):
                        sanitize = getattr(mod, 'sanitize_filename')
                        break
            except Exception:
                pass

        if sanitize is None:
            self.fail('sanitize_filename not found in openhands.server modules')

        # 1) Directory traversal components should be removed (basename)
        self.assertEqual(sanitize('../../etc/passwd'), 'passwd')

        # 2) Non-allowed characters (spaces, punctuation) should be stripped, but dots, hyphens, underscores kept
        self.assertEqual(sanitize('my file @#$.txt'), 'myfile.txt')
        self.assertEqual(sanitize('some-name_with.chars!!.pdf'), 'some-name_with.chars.pdf')

        # 3) Very long filenames should be truncated to <= 255 and preserve the extension
        long_input = '/tmp/' + ('a' * 260) + '.ext'
        result = sanitize(long_input)
        self.assertTrue(len(result) <= 255)
        self.assertTrue(result.endswith('.ext'))
        # ensure no directory separators remain
        self.assertNotIn('/', result)
        self.assertNotIn('\\', result)
