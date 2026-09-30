import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.skills.deep_research')
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
        """trim_context_to_word_limit keeps the most recent items without exceeding max_words"""
        # Import the module under test using __import__ to avoid top-level import statements
        deep_research_module = __import__("gpt_researcher.skills.deep_research", fromlist=["*"])

        context = ["first", "two words", "three words here"]

        # With max_words=5, the last two items (2 + 3 words) should be included in original order
        result = deep_research_module.trim_context_to_word_limit(context, max_words=5)
        self.assertEqual(result, ["two words", "three words here"])

        # With max_words=3, only the most recent item (3 words) fits
        result = deep_research_module.trim_context_to_word_limit(context, max_words=3)
        self.assertEqual(result, ["three words here"])

        # With max_words=0, nothing fits
        result = deep_research_module.trim_context_to_word_limit(context, max_words=0)
        self.assertEqual(result, [])

        # Also verify it handles non-string items (count_words supports lists)
        context2 = ["one", ["two", "words"], "last one"]
        # counts: 1, 2, 2 -> with max_words=4 should include ["two words" list, "last one"]
        result = deep_research_module.trim_context_to_word_limit(context2, max_words=4)
        self.assertEqual(result, [["two", "words"], "last one"])
