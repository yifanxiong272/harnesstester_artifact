import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('backend.utils')
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
        """Ensure non-string input is converted to string before writing."""
        class DummyFile:
            def __init__(self):
                self.written = ""

            async def write(self, s):
                # mimic aiofiles' write behavior
                self.written += s
                return len(s)

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        async def run():
            dummy = DummyFile()
            # Patch aiofiles.open to return our async context manager
            with unittest.mock.patch("aiofiles.open", new=lambda *args, **kwargs: dummy):
                await write_to_file("ignored_filename.txt", 12345)  # int, not str
            return dummy.written

        asyncio = __import__('asyncio')
        loop = asyncio.get_event_loop()
        written = loop.run_until_complete(run())
        self.assertEqual(written, "12345")
