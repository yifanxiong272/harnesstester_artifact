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
        """Test that write_text_to_md constructs the expected path, calls write_to_file and returns the quoted path."""
        called = {}

        async def fake_write_to_file(filename, text):
            called['filename'] = filename
            called['text'] = text

        # Patch the write_to_file used by write_text_to_md
        original = write_text_to_md.__globals__.get('write_to_file')
        write_text_to_md.__globals__['write_to_file'] = fake_write_to_file

        try:
            text = "Hello, world 😊"
            long_filename = "x" * 70  # longer than 60 chars to exercise slicing
            expected_path = f"outputs/{long_filename[:60]}.md"

            # Get asyncio without a top-level import
            asyncio = __import__('asyncio')

            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(write_text_to_md(text, long_filename))
            finally:
                loop.close()

            # Use the same urllib.quote used in the function under test
            quote = write_text_to_md.__globals__['urllib'].parse.quote

            self.assertEqual(result, quote(expected_path))
            self.assertEqual(called.get('filename'), expected_path)
            self.assertEqual(called.get('text'), text)
        finally:
            # Restore original function to avoid side effects
            if original is None:
                # remove the patched name if it wasn't present before
                try:
                    del write_text_to_md.__globals__['write_to_file']
                except KeyError:
                    pass
            else:
                write_text_to_md.__globals__['write_to_file'] = original
