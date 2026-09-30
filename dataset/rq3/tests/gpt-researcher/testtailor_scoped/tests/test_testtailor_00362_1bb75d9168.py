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
    @patch('gpt_researcher.agent.ImageGenerator')
    @patch('gpt_researcher.agent.SourceCurator')
    @patch('gpt_researcher.agent.BrowserManager')
    @patch('gpt_researcher.agent.ContextManager')
    @patch('gpt_researcher.agent.ReportGenerator')
    @patch('gpt_researcher.agent.ResearchConductor')
    @patch('gpt_researcher.agent.Memory')
    @patch('gpt_researcher.agent.get_retrievers')
    @patch('gpt_researcher.agent.VectorStoreWrapper')
    @patch('gpt_researcher.agent.get_prompt_family')
    @patch('gpt_researcher.agent.Config')
    @patch('logging.getLogger')
    def test_case_XX(
        self,
        mock_getLogger,
        mock_Config,
        mock_get_prompt_family,
        mock_VectorStoreWrapper,
        mock_get_retrievers,
        mock_Memory,
        mock_ResearchConductor,
        mock_ReportGenerator,
        mock_ContextManager,
        mock_BrowserManager,
        mock_SourceCurator,
        mock_ImageGenerator
    ):
        """Ensure that providing mcp_strategy='comprehensive' returns 'deep' and logs a deprecation warning."""
        # Prepare mocks for configuration and components used during initialization
        config_mock = MagicMock()
        config_mock.prompt_family = 'default'
        # attributes accessed in __init__
        config_mock.embedding_provider = 'ep'
        config_mock.embedding_model = 'em'
        config_mock.embedding_kwargs = {}
        config_mock.smart_llm_model = 'model'
        config_mock.smart_token_limit = 1000
        config_mock.smart_llm_provider = 'provider'
        config_mock.llm_kwargs = {}
        config_mock.set_verbose = MagicMock()
        mock_Config.return_value = config_mock

        # Prompt family stub
        prompt_family_mock = MagicMock()
        mock_get_prompt_family.return_value = prompt_family_mock

        # Other component stubs to allow __init__ to complete without side effects
        mock_VectorStoreWrapper.return_value = MagicMock()
        mock_get_retrievers.return_value = ['web']
        mock_Memory.return_value = MagicMock()
        mock_ResearchConductor.return_value = MagicMock()
        mock_ReportGenerator.return_value = MagicMock()
        mock_ContextManager.return_value = MagicMock()
        mock_BrowserManager.return_value = MagicMock()
        mock_SourceCurator.return_value = MagicMock()

        image_generator_instance = MagicMock()
        image_generator_instance.is_enabled.return_value = False
        mock_ImageGenerator.return_value = image_generator_instance

        # Configure logger mock to capture warnings
        logger_mock = MagicMock()
        mock_getLogger.return_value = logger_mock

        # Instantiate GPTResearcher with the legacy 'comprehensive' strategy
        researcher = GPTResearcher(query="test query", mcp_strategy="comprehensive")

        # Assert that the resolved strategy is "deep"
        self.assertEqual(researcher.mcp_strategy, "deep")

        # Assert that the deprecation warning was logged with the expected message
        logger_mock.warning.assert_called_with("mcp_strategy 'comprehensive' is deprecated, use 'deep' instead")
