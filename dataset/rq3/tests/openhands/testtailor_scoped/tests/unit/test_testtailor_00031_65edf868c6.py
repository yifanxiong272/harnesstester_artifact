import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.server.session.session')
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
        """Ensure initialize_agent copies git_user_name from settings into config."""
        # Prepare a minimal settings-like object with git_user_name set
        settings = type('S', (), {})()
        settings.agent = 'test_agent'
        settings.confirmation_mode = None
        settings.security_analyzer = None
        settings.sandbox_base_container_image = None
        settings.sandbox_runtime_container_image = None
        settings.max_iterations = None
        settings.max_budget_per_task = None
        settings.search_api_key = None
        settings.sandbox_api_key = None
        settings.enable_default_condenser = False
        settings.condenser_max_size = None
        settings.mcp_config = None
        settings.git_user_name = 'Alice'
        settings.git_user_email = None

        # Create a WebSession-like instance without running its __init__
        ws = WebSession.__new__(WebSession)

        # Minimal agent_session mock with event_stream.add_event and an async start
        class _EventStream:
            def add_event(self, *args, **kwargs):
                return None

        async def fake_start(*args, **kwargs):
            return None

        ws.agent_session = type('AS', (), {})()
        ws.agent_session.event_stream = _EventStream()
        ws.agent_session.start = fake_start

        # Minimal config mock with required attributes and methods
        class _MCP:
            def __init__(self):
                self.shttp_servers = []
                self.stdio_servers = []

            def merge(self, other):
                return self

            def __repr__(self):
                return "<mcp>"

        class _Security:
            def __init__(self):
                self.confirmation_mode = False
                self.security_analyzer = None

        class _Sandbox:
            def __init__(self):
                self.base_container_image = 'base_img'
                self.runtime_container_image = 'runtime_img'
                self.api_key = None

        class _Config:
            def __init__(self):
                self.default_agent = 'test_agent'
                self.security = _Security()
                self.sandbox = _Sandbox()
                self.search_api_key = None
                self.mcp_host = 'host'
                self.mcp = _MCP()
                self.runtime = 'runtime'
                self.client_wait_timeout = 0.1
                self.max_budget_per_task = None
                # Provide max_iterations to avoid AttributeError
                self.max_iterations = 5

            def get_agent_config(self, agent_cls):
                # return an object that allows setting attributes like runtime and condenser
                return type('AC', (), {'runtime': None, 'condenser': None})()

            def get_llm_config_from_agent(self, agent_name):
                return type('LLMConf', (), {'model': 'm', 'base_url': 'b'})()

            def get_agent_to_llm_config_map(self):
                return {}

            def get_agent_configs(self):
                return []

        ws.config = _Config()

        # Minimal llm_registry mock required by Agent.__init__
        class _LLMRegistry:
            def __init__(self):
                self.retry_listner = None

            def get_llm_from_agent_config(self, service_id, agent_config):
                # return a simple object with a config attribute used by Agent.__init__
                return type('LLM', (), {'config': type('C', (), {'model': 'm', 'base_url': 'b'})()})

        ws.llm_registry = _LLMRegistry()

        # Simple logger with required methods
        class _Logger:
            def debug(self, *a, **k):
                pass

            def info(self, *a, **k):
                pass

            def exception(self, *a, **k):
                pass

            def error(self, *a, **k):
                pass

        ws.logger = _Logger()

        # Helpers used by initialize_agent
        ws.user_id = None

        async def dummy_send_error(msg):
            # should not be called in this success path
            raise AssertionError("send_error called unexpectedly with: " + str(msg))

        ws.send_error = dummy_send_error

        # Ensure a test agent is registered
        class DummyAgent(Agent):
            def __init__(self, config, llm_registry):
                super().__init__(config, llm_registry)

            def step(self, state):
                return None

        # Register only if not already registered to avoid collisions across tests
        if 'test_agent' not in Agent._registry:
            Agent.register('test_agent', DummyAgent)

        # Patch OpenHandsMCPConfigImpl.create_default_mcp_server_config to avoid external calls
        original_create = getattr(OpenHandsMCPConfigImpl, 'create_default_mcp_server_config', None)

        async def fake_create_default_mcp_server_config(*args, **kwargs):
            return (None, [])  # no default MCP server added

        setattr(OpenHandsMCPConfigImpl, 'create_default_mcp_server_config', fake_create_default_mcp_server_config)

        # Run the async initialize_agent and assert the git user name copied
        try:
            asyncio.run(ws.initialize_agent(settings, None, None))
            self.assertEqual(ws.config.git_user_name, 'Alice')
        finally:
            # Restore patched function to avoid side effects
            if original_create is not None:
                setattr(OpenHandsMCPConfigImpl, 'create_default_mcp_server_config', original_create)
