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
        """Ensure _process_mcp_configs is called during init and updates cfg.retrievers."""
        # Patch heavy external dependencies used during initialization so __init__ can run safely.
        with patch('gpt_researcher.agent.Config') as mock_config_cls, \
             patch('gpt_researcher.agent.get_retrievers') as mock_get_retrievers, \
             patch('gpt_researcher.agent.get_prompt_family') as mock_get_prompt_family, \
             patch('gpt_researcher.agent.Memory') as mock_memory, \
             patch('gpt_researcher.agent.ResearchConductor') as mock_research_conductor, \
             patch('gpt_researcher.agent.ReportGenerator') as mock_report_generator, \
             patch('gpt_researcher.agent.ContextManager') as mock_context_manager, \
             patch('gpt_researcher.agent.BrowserManager') as mock_browser_manager, \
             patch('gpt_researcher.agent.SourceCurator') as mock_source_curator, \
             patch('gpt_researcher.agent.ImageGenerator') as mock_image_generator:

            # Configure the fake Config instance
            cfg_instance = MagicMock()
            # Start with a comma-separated retrievers string to trigger parsing branch
            cfg_instance.retrievers = "web,local"
            cfg_instance.prompt_family = 'pfamily'
            cfg_instance.embedding_provider = 'embed_prov'
            cfg_instance.embedding_model = 'embed_model'
            cfg_instance.embedding_kwargs = {}
            cfg_instance.smart_llm_model = 'smart_model'
            cfg_instance.smart_llm_provider = 'smart_provider'
            cfg_instance.smart_token_limit = 512
            cfg_instance.llm_kwargs = {}
            cfg_instance.set_verbose = MagicMock()
            mock_config_cls.return_value = cfg_instance

            # Other patched functions/constructors return simple placeholders
            mock_get_retrievers.return_value = ['web']
            mock_get_prompt_family.return_value = MagicMock()
            mock_memory.return_value = MagicMock()
            mock_research_conductor.return_value = MagicMock()
            mock_report_generator.return_value = MagicMock()
            mock_context_manager.return_value = MagicMock()
            mock_browser_manager.return_value = MagicMock()
            mock_source_curator.return_value = MagicMock()
            mock_image_generator.return_value = MagicMock(is_enabled=MagicMock(return_value=False))

            # Provide a sample mcp_configs to trigger _process_mcp_configs path
            sample_mcp_configs = [{
                "command": "python",
                "args": ["my_mcp_server.py"],
                "name": "search"
            }]

            # Instantiate the researcher with mcp_configs; __init__ should call _process_mcp_configs
            researcher = GPTResearcher(query="test query", mcp_configs=sample_mcp_configs)

            # After initialization, the cfg.retrievers should have been converted to a list and include "mcp"
            self.assertIsNotNone(researcher.mcp_configs)
            self.assertEqual(researcher.mcp_configs, sample_mcp_configs)

            # The mock cfg_instance.retrievers should have been updated to contain 'mcp'
            # Since original was "web,local", expect list ['web','local','mcp']
            self.assertEqual(cfg_instance.retrievers, ['web', 'local', 'mcp'])
