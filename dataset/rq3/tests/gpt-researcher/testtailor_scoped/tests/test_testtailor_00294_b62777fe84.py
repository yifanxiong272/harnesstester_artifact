import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.skills.context_manager')
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
        """Test that get_similar_written_contents_by_draft_section_titles
        gathers results for the current subtopic and draft section titles,
        deduplicates them, and respects the max_results limit.
        """
        # Setup a minimal researcher object with the kwargs attribute used by the method.
        researcher = type("R", (), {})()
        researcher.kwargs = {}

        cm = ContextManager(researcher)

        # Prepare a fake async implementation for the private method that returns
        # lists of strings (some duplicates across queries to test deduplication).
        async def fake_get_similar(query, written_contents, similarity_threshold=0.5, max_results=10, **kwargs):
            if query == "topic":
                return ["common", "topic-only"]
            if query == "sec1":
                return ["common", "sec1-only"]
            if query == "sec2":
                return ["other", "sec2-only", "common"]
            return []

        # Patch the private method on our ContextManager instance.
        setattr(cm, "_ContextManager__get_similar_written_contents_by_query", fake_get_similar)

        # Some dummy written_contents (not used by our fake but passed for signature compatibility).
        written_contents = [{"id": 1, "text": "a"}, {"id": 2, "text": "b"}]

        # Run the async method in a fresh event loop to avoid interfering with any existing loop.
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                cm.get_similar_written_contents_by_draft_section_titles(
                    current_subtopic="topic",
                    draft_section_titles=["sec1", "sec2"],
                    written_contents=written_contents,
                    max_results=4,
                )
            )
        finally:
            loop.close()

        # Assertions:
        # - Result is a list
        # - Contains the deduplicated item 'common'
        # - Has no duplicates
        # - Honors the max_results limit
        self.assertIsInstance(result, list)
        self.assertIn("common", result)
        self.assertEqual(len(result), len(set(result)))
        self.assertLessEqual(len(result), 4)
