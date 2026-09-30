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
        """Ensure DeepResearchSkill is instantiated when report_type is DeepResearch"""
        # Patch the heavy external dependencies used during initialization
        with patch('gpt_researcher.agent.Config') as mock_config, \
             patch('gpt_researcher.agent.get_prompt_family') as mock_get_prompt_family, \
             patch('gpt_researcher.agent.get_retrievers') as mock_get_retrievers, \
             patch('gpt_researcher.agent.Memory') as mock_memory, \
             patch('gpt_researcher.agent.ResearchConductor') as mock_research_conductor, \
             patch('gpt_researcher.agent.ReportGenerator') as mock_report_generator, \
             patch('gpt_researcher.agent.ContextManager') as mock_context_manager, \
             patch('gpt_researcher.agent.BrowserManager') as mock_browser_manager, \
             patch('gpt_researcher.agent.SourceCurator') as mock_source_curator, \
             patch('gpt_researcher.agent.ImageGenerator') as mock_image_generator, \
             patch('gpt_researcher.agent.DeepResearchSkill') as mock_deep_skill:

            # Configure Config mock to provide required attributes
            cfg_instance = MagicMock()
            cfg_instance.prompt_family = "pf"
            cfg_instance.embedding_provider = "emb_provider"
            cfg_instance.embedding_model = "emb_model"
            cfg_instance.embedding_kwargs = {}
            cfg_instance.smart_llm_model = "model"
            cfg_instance.smart_llm_provider = "prov"
            cfg_instance.smart_token_limit = 1024
            cfg_instance.llm_kwargs = {}
            mock_config.return_value = cfg_instance

            # Minimal returns for other factories
            mock_get_prompt_family.return_value = MagicMock()
            mock_get_retrievers.return_value = ["dummy_retriever"]
            mock_memory.return_value = MagicMock()
            mock_research_conductor.return_value = MagicMock()
            mock_report_generator.return_value = MagicMock()
            mock_context_manager.return_value = MagicMock()
            mock_browser_manager.return_value = MagicMock()
            mock_source_curator.return_value = MagicMock()
            mock_image_generator.return_value = MagicMock()

            # DeepResearchSkill should return a sentinel instance so we can assert identity
            deep_instance = MagicMock()
            mock_deep_skill.return_value = deep_instance

            # Now create researcher with DeepResearch report type
            researcher = GPTResearcher(query="deep dive", report_type=ReportType.DeepResearch.value)

            # Assertions: deep_researcher should be the instance returned by DeepResearchSkill
            self.assertIs(researcher.deep_researcher, deep_instance)
            # And DeepResearchSkill should have been called exactly once with the researcher instance
            mock_deep_skill.assert_called_once()
            called_arg = mock_deep_skill.call_args[0][0]
            self.assertIs(called_arg, researcher)
