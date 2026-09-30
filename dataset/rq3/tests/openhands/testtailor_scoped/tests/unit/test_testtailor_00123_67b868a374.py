import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.storage.local')
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
        """Ensure temp file is removed when os.replace fails during atomic write."""
        # Create a unique directory under the current working directory to avoid needing tempfile
        temp_dir = os.path.join(
            os.getcwd(),
            f"test_localfilestore_{os.getpid()}_{threading.get_ident()}_{id(self)}",
        )
        os.makedirs(temp_dir, exist_ok=True)
        try:
            store = LocalFileStore(temp_dir)
            path = 'some/deep/dir/file.txt'
            contents = 'hello-world'

            full_path = store.get_full_path(path)
            temp_path = f'{full_path}.tmp.{os.getpid()}.{threading.get_ident()}'

            # Cause os.replace to raise so the except block runs and should remove temp_path
            with patch.object(os, 'replace', side_effect=RuntimeError('replace failed')):
                with self.assertRaises(RuntimeError):
                    store.write(path, contents)

            # The temp file must have been removed by the exception handler
            self.assertFalse(os.path.exists(temp_path))
            # The final target file must not have been created due to the replace failure
            self.assertFalse(os.path.exists(full_path))
        finally:
            # Best-effort cleanup
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
