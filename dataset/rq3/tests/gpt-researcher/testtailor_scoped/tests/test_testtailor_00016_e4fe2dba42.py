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
        """Ensure providing mcp_configs triggers _process_mcp_configs behavior:
           - researcher.mcp_configs is stored
           - 'mcp' is added to cfg.retrievers (as list or in comma string)
           - no new environment variables starting with 'MCP' are added (no env pollution)
        """
        # Prepare a sample MCP config
        sample_mcp = [{"command": "python", "args": ["my_mcp_server.py"], "name": "search"}]

        # Snapshot env keys that start with 'MCP' to ensure no env pollution
        env_mcp_keys_before = {k for k in os.environ.keys() if k.startswith("MCP")}

        # Define a lightweight dummy Config to avoid file/io and heavy initialization
        class DummyConfig:
            def __init__(self, path=None):
                self.prompt_family = "default"
                self.embedding_provider = "dummy"
                self.embedding_model = "dummy-model"
                self.embedding_kwargs = {}
                self.retrievers = None
                self.mcp_strategy = None
                self.smart_llm_model = "gpt"
                self.smart_llm_provider = "openai"
                self.smart_token_limit = 512
                self.llm_kwargs = {}

            def set_verbose(self, v):
                self._verbose = v

        # Patch heavy components to simple mocks so __init__ completes without external dependencies
        with patch('gpt_researcher.agent.Config', new=DummyConfig), \
             patch('gpt_researcher.agent.Memory') as mock_memory, \
             patch('gpt_researcher.agent.ResearchConductor') as mock_rc, \
             patch('gpt_researcher.agent.ReportGenerator') as mock_rg, \
             patch('gpt_researcher.agent.ContextManager') as mock_cm, \
             patch('gpt_researcher.agent.BrowserManager') as mock_bm, \
             patch('gpt_researcher.agent.SourceCurator') as mock_sc, \
             patch('gpt_researcher.agent.ImageGenerator') as mock_ig, \
             patch('gpt_researcher.agent.DeepResearchSkill') as mock_dr, \
             patch('gpt_researcher.agent.get_retrievers', return_value=['web']) as mock_get_retrievers:

            # Ensure Memory mock doesn't raise and returns a simple object
            mock_memory.return_value = MagicMock()

            # Initialize researcher with mcp_configs to trigger _process_mcp_configs
            researcher = GPTResearcher(query="test mcp", mcp_configs=sample_mcp)

        # The mcp_configs should be stored on the researcher instance
        self.assertEqual(researcher.mcp_configs, sample_mcp)

        # The config retrievers should include 'mcp' (support both list and comma-separated string)
        self.assertTrue(hasattr(researcher.cfg, "retrievers"))
        cfg_retrievers = researcher.cfg.retrievers
        if isinstance(cfg_retrievers, str):
            parsed = [r.strip() for r in cfg_retrievers.split(",") if r.strip()]
            self.assertIn("mcp", parsed)
        else:
            self.assertIn("mcp", cfg_retrievers)

        # Ensure no new environment variables starting with 'MCP' were added
        env_mcp_keys_after = {k for k in os.environ.keys() if k.startswith("MCP")}
        self.assertEqual(env_mcp_keys_before, env_mcp_keys_after)
