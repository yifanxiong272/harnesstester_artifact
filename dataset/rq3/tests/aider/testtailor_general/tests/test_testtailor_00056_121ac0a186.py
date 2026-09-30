import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.editblock_coder')
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
    def test_try_dotdotdots_replaces_elided_chunks(self):
        """Ensure replace_most_similar_chunk handles elided (...) chunks via try_dotdotdots."""
        from aider.coders import editblock_coder as eb

        whole = "header\nold1\nmiddle\nlineZ\nfooter\n"
        part = "old1\n...\nlineZ\n"
        replace = "new1\n...\nlineZ2\n"

        expected = "header\nnew1\nmiddle\nlineZ2\nfooter\n"

        result = eb.replace_most_similar_chunk(whole, part, replace)
        self.assertEqual(result, expected)
