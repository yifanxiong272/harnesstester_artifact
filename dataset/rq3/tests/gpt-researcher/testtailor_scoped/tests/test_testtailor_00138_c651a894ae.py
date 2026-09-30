import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.agent')
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
        """Ensure _generate_research_id sets and caches an ID when _research_id is empty,
        and that the ID has the expected format (prefix + 12 hex chars)."""
        # Minimal dummy Config to satisfy GPTResearcher __init__ expectations
        class DummyConfig:
            def __init__(self, path=None):
                self.prompt_family = "default"
                self.embedding_provider = "none"
                self.embedding_model = "none"
                self.embedding_kwargs = {}
                # attributes referenced elsewhere but not used in this test
                self.smart_llm_model = "model"
                self.smart_llm_provider = "provider"
                self.smart_token_limit = 1000
                self.llm_kwargs = {}
                self.retrievers = ["dummy"]

            def set_verbose(self, v):
                self._verbose = v

        # Patch heavy or external dependencies so initialization is lightweight
        with patch('time.time', return_value=123456.789), \
             patch('gpt_researcher.agent.Config', new=DummyConfig), \
             patch('gpt_researcher.agent.Memory', new=MagicMock()), \
             patch('gpt_researcher.agent.get_retrievers', return_value=['dummy']), \
             patch('gpt_researcher.agent.get_prompt_family', return_value=MagicMock()), \
             patch('gpt_researcher.agent.ResearchConductor', new=MagicMock()), \
             patch('gpt_researcher.agent.ReportGenerator', new=MagicMock()), \
             patch('gpt_researcher.agent.ContextManager', new=MagicMock()), \
             patch('gpt_researcher.agent.BrowserManager', new=MagicMock()), \
             patch('gpt_researcher.agent.SourceCurator', new=MagicMock()), \
             patch('gpt_researcher.agent.ImageGenerator', new=MagicMock()):
            # Instantiate researcher; heavy parts are mocked out
            researcher = GPTResearcher(query="unique query")

            # Initially _research_id should be empty
            self.assertEqual(researcher._research_id, "")

            # Generate ID (this should exercise the branch that creates the id)
            research_id = researcher._generate_research_id()

            # ID should start with expected prefix
            self.assertTrue(research_id.startswith("research_"))

            # Suffix length should be 12 hex characters
            suffix = research_id.split("research_", 1)[1]
            self.assertEqual(len(suffix), 12)

            # All characters in suffix should be valid hex digits (lowercase)
            hex_chars = "0123456789abcdef"
            self.assertTrue(all(c in hex_chars for c in suffix))

            # Subsequent calls should return the same cached ID and not regenerate
            self.assertEqual(researcher._generate_research_id(), research_id)
            self.assertEqual(researcher._research_id, research_id)
