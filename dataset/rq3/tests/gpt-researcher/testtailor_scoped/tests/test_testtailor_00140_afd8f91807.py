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
        """Test that when DocumentLoader.path is a list containing an existing file,
        the loader schedules _load_document and returns the expected document structure.
        """
        # create a real file in the current working directory so os.path.isfile(file_path) is True
        file_name = "sample_test_file_for_loader.tmp"
        file_path = os.path.abspath(file_name)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("dummy content")

            # instantiate with a list path to hit the target branch
            loader = DocumentLoader([file_path])

            # simple page-like object expected by DocumentLoader.load
            class Page:
                def __init__(self, content, source):
                    self.page_content = content
                    self.metadata = {"source": source}

            # replace _load_document with a coroutine that returns one page
            async def fake_load_document(file_path_arg, file_extension):
                return [Page("my loaded content", file_path_arg)]

            loader._load_document = fake_load_document

            # run the async load and assert returned structure
            docs = asyncio.run(loader.load())
            self.assertIsInstance(docs, list)
            self.assertEqual(len(docs), 1)
            self.assertEqual(docs[0]["raw_content"], "my loaded content")
            self.assertEqual(docs[0]["url"], os.path.basename(file_path))
        finally:
            # cleanup the file created for the test
            try:
                os.remove(file_path)
            except Exception:
                pass
