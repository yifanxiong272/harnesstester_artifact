import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.document.document')
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
        # create a temporary .txt file in the current working directory so
        # isinstance(self.path, list) branch is taken and os.path.isfile(file_path) is True
        file_name = f"tmp_docloader_test_{os.getpid()}.txt"
        file_path = os.path.join(os.getcwd(), file_name)
        try:
            with open(file_path, "wb") as f:
                f.write(b"Hello world from test")

            loader = DocumentLoader([file_path])
            docs = asyncio.get_event_loop().run_until_complete(loader.load())

            self.assertIsInstance(docs, list)
            self.assertGreaterEqual(len(docs), 1)
            first = docs[0]
            self.assertIn("raw_content", first)
            self.assertIn("url", first)
            self.assertIn("Hello world", first["raw_content"])
            self.assertEqual(first["url"], os.path.basename(file_path))
        finally:
            try:
                os.unlink(file_path)
            except Exception:
                pass
