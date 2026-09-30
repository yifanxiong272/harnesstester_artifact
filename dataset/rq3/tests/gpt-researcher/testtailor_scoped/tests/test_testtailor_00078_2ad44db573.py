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
        """Ensure DeepResearchSkill is initialized when report_type is DeepResearch."""
        # Patch a large set of dependencies to keep initialization lightweight and deterministic
        with patch('gpt_researcher.agent.Config') as mock_Config, \
             patch('gpt_researcher.agent.get_prompt_family') as mock_get_pf, \
             patch('gpt_researcher.agent.get_retrievers') as mock_get_retrievers, \
             patch('gpt_researcher.agent.Memory') as mock_Memory, \
             patch('gpt_researcher.agent.ResearchConductor') as mock_ResearchConductor, \
             patch('gpt_researcher.agent.ReportGenerator') as mock_ReportGenerator, \
             patch('gpt_researcher.agent.ContextManager') as mock_ContextManager, \
             patch('gpt_researcher.agent.BrowserManager') as mock_BrowserManager, \
             patch('gpt_researcher.agent.SourceCurator') as mock_SourceCurator, \
             patch('gpt_researcher.agent.ImageGenerator') as mock_ImageGenerator, \
             patch('gpt_researcher.agent.DeepResearchSkill') as mock_DeepResearchSkill, \
             patch('gpt_researcher.agent.ReportType') as mock_ReportType:

            # Configure the mocked ReportType enum to expose the DeepResearch.value
            mock_ReportType.DeepResearch = MagicMock()
            mock_ReportType.DeepResearch.value = "deep_research_value"

            # Configure Config instance returned
            cfg_instance = MagicMock()
            cfg_instance.set_verbose = MagicMock()
            cfg_instance.prompt_family = "default_pf"
            # attributes used by Memory/other components
            cfg_instance.embedding_provider = "embedprov"
            cfg_instance.embedding_model = "embedmodel"
            cfg_instance.embedding_kwargs = {}
            cfg_instance.smart_llm_model = "smart_model"
            cfg_instance.smart_llm_provider = "smart_provider"
            cfg_instance.smart_token_limit = 128
            cfg_instance.llm_kwargs = {}
            cfg_instance.retrievers = ["web"]
            cfg_instance.mcp_strategy = None
            mock_Config.return_value = cfg_instance

            # Prompt family mock
            mock_get_pf.return_value = MagicMock()

            # Retrievers and Memory mocks
            mock_get_retrievers.return_value = ["web"]
            mock_Memory.return_value = MagicMock()

            # Component constructor mocks (return simple MagicMocks)
            mock_ResearchConductor.return_value = MagicMock()
            mock_ReportGenerator.return_value = MagicMock()
            mock_ContextManager.return_value = MagicMock()
            mock_BrowserManager.return_value = MagicMock()
            mock_SourceCurator.return_value = MagicMock()

            # Image generator: disabled to avoid generation during constructor
            img_inst = MagicMock()
            img_inst.is_enabled.return_value = False
            mock_ImageGenerator.return_value = img_inst

            # DeepResearchSkill mock instance
            deep_inst = MagicMock()
            mock_DeepResearchSkill.return_value = deep_inst

            # Instantiate GPTResearcher with the patched ReportType value to trigger deep research branch
            researcher = GPTResearcher(query="test deep", report_type=mock_ReportType.DeepResearch.value)

            # Assertions: deep_researcher should be set and should be the returned mock instance
            self.assertIsNotNone(researcher.deep_researcher, "deep_researcher should be initialized for DeepResearch report_type")
            self.assertIs(researcher.deep_researcher, deep_inst, "deep_researcher should be the instance returned by DeepResearchSkill()")
            # Ensure DeepResearchSkill was called with the researcher instance
            mock_DeepResearchSkill.assert_called_once_with(researcher)
