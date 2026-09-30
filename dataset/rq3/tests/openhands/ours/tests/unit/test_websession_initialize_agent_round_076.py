import asyncio
from types import SimpleNamespace
import pytest

import openhands.server.session.session as session_mod


class DummyLogger:
    def __init__(self):
        self.debug_msgs = []
        self.info_msgs = []
        self.exception_msgs = []

    def debug(self, msg):
        self.debug_msgs.append(msg)

    def info(self, msg):
        self.info_msgs.append(msg)

    def exception(self, msg):
        self.exception_msgs.append(msg)


class FakeEventStream:
    def __init__(self):
        self.events = []

    def add_event(self, ev, src):
        # record events for assertion
        self.events.append((ev, src))


class FakeAgentSession:
    def __init__(self):
        self.event_stream = FakeEventStream()
        self.start_called = False
        self.start_kwargs = None
        # will be set to an async function in tests to control behavior
        self.start_impl = None

    async def start(self, *args, **kwargs):
        self.start_called = True
        self.start_kwargs = dict(kwargs)
        if self.start_impl:
            return await self.start_impl(*args, **kwargs)
        return None


class DummyMCP:
    def __init__(self):
        self.shttp_servers = []
        self.stdio_servers = []
        self.merged_with = None

    def merge(self, other):
        # emulate merge returning a new MCP-like object
        new = DummyMCP()
        new.shttp_servers = list(self.shttp_servers)
        new.stdio_servers = list(self.stdio_servers)
        new.merged_with = other
        return new


class DummySandbox:
    def __init__(self):
        self.base_container_image = 'base'
        self.runtime_container_image = 'runtime'
        self.api_key = None


class DummySecurity:
    def __init__(self):
        self.confirmation_mode = 'old'
        self.security_analyzer = 'old_analyzer'


class DummyConfig:
    def __init__(self):
        self.default_agent = None
        self.security = DummySecurity()
        self.sandbox = DummySandbox()
        self.mcp = DummyMCP()
        self.mcp_host = 'host'
        self.runtime = 'dummy-runtime'
        self.max_budget_per_task = 5
        self.max_iterations = 10
        self.git_user_name = None
        self.git_user_email = None
        self.search_api_key = None

    def get_agent_config(self, agent_cls):
        ac = SimpleNamespace()
        ac.runtime = None
        ac.condenser = None
        return ac

    def get_llm_config_from_agent(self, agent_name):
        # return an object with model and base_url for logging/LLM config
        return SimpleNamespace(model='m', base_url='u')

    def get_agent_to_llm_config_map(self):
        return {}

    def get_agent_configs(self):
        return {}


class FakeAgentClass:
    def __init__(self, agent_config, llm_registry):
        self.agent_config = agent_config
        self.llm_registry = llm_registry


@pytest.mark.asyncio
async def test_initialize_agent_success_flow_round_076(monkeypatch):
    """
    Exercise the successful path through initialize_agent that updates git fields,
    sandbox api key, merges mcp_config, appends the default OpenHands MCP server,
    and enables the default condenser.
    """
    # Prepare a dummy self object with all attributes referenced by the method
    dummy = SimpleNamespace()
    dummy.logger = DummyLogger()
    dummy.agent_session = FakeAgentSession()
    dummy.config = DummyConfig()
    dummy.llm_registry = SimpleNamespace()
    dummy.user_id = 'user-x'
    dummy._notify_on_llm_retry = lambda *args, **kwargs: None

    # record send_error calls
    dummy.send_error_calls = []

    async def _send_error(msg):
        dummy.send_error_calls.append(msg)

    dummy.send_error = _send_error

    # Patch OpenHandsMCPConfigImpl.create_default_mcp_server_config to return truthy server
    async def fake_create_default(host, cfg, user_id):
        return ('openhands_server_obj', ['stdio_obj'])

    monkeypatch.setattr(
        session_mod.OpenHandsMCPConfigImpl,
        'create_default_mcp_server_config',
        fake_create_default,
    )

    # Patch Agent.get_cls to return our FakeAgentClass
    monkeypatch.setattr(session_mod.Agent, 'get_cls', lambda cls: FakeAgentClass)

    # Prepare settings with values to trigger branches
    # Use SimpleNamespace for settings (no ConversationInitData behavior here)
    settings = SimpleNamespace(
        agent=None,
        confirmation_mode=None,
        security_analyzer=None,
        sandbox_base_container_image=None,
        sandbox_runtime_container_image=None,
        git_user_name='git-name',
        git_user_email='git-email',
        max_iterations=None,
        max_budget_per_task=None,
        search_api_key='search-key',
        sandbox_api_key=SimpleNamespace(get_secret_value=lambda: 'secret-abc'),
        mcp_config={'custom': 'cfg'},
        enable_default_condenser=True,
        condenser_max_size=None,
    )

    # Ensure agent_session.start does not raise
    async def start_ok(**kwargs):
        return 'ok'

    dummy.agent_session.start_impl = lambda *a, **k: start_ok(**k)

    # Call the coroutine under test
    await session_mod.WebSession.initialize_agent(dummy, settings, initial_message='init', replay_json='rj')

    # Assertions on config updates
    assert dummy.config.git_user_name == 'git-name'
    assert dummy.config.git_user_email == 'git-email'
    # sandbox api key should be set via get_secret_value()
    assert dummy.config.sandbox.api_key == 'secret-abc'
    # mcp.merge should have been called; merged instance records merged_with
    assert dummy.config.mcp.merged_with == {'custom': 'cfg'}
    # default OpenHands MCP server appended
    assert 'openhands_server_obj' in dummy.config.mcp.shttp_servers
    assert 'stdio_obj' in dummy.config.mcp.stdio_servers
    # agent_session.start should have been called with provided arguments
    assert dummy.agent_session.start_called is True
    assert dummy.agent_session.start_kwargs['initial_message'] == 'init'
    assert dummy.agent_session.start_kwargs['replay_json'] == 'rj'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc, expected_msg",
    [
        (session_mod.MicroagentValidationError('micro bad'), 'Failed to create agent session: micro bad'),
        (ValueError('microagent broken'), 'Failed to create agent session: microagent broken'),
        (ValueError('other error'), 'Failed to create agent session: ValueError'),
        (RuntimeError('boom'), 'Failed to create agent session: RuntimeError'),
    ],
)
async def test_initialize_agent_exception_paths_round_076(monkeypatch, exc, expected_msg):
    """
    Trigger different exceptions from agent_session.start and assert send_error
    behavior for MicroagentValidationError, ValueError (with microagent), ValueError
    (other), and a generic Exception.
    """
    dummy = SimpleNamespace()
    dummy.logger = DummyLogger()
    dummy.agent_session = FakeAgentSession()
    dummy.config = DummyConfig()
    dummy.llm_registry = SimpleNamespace()
    dummy.user_id = 'user-y'
    dummy._notify_on_llm_retry = lambda *args, **kwargs: None

    dummy.send_error_calls = []

    async def _send_error(msg):
        dummy.send_error_calls.append(msg)

    dummy.send_error = _send_error

    # Patch create_default_mcp_server_config to a no-op (returns no server)
    async def fake_create_default(host, cfg, user_id):
        return (None, [])

    monkeypatch.setattr(
        session_mod.OpenHandsMCPConfigImpl,
        'create_default_mcp_server_config',
        fake_create_default,
    )

    # Make Agent.get_cls return FakeAgentClass so agent construction is stable
    monkeypatch.setattr(session_mod.Agent, 'get_cls', lambda cls: FakeAgentClass)

    # settings minimal
    settings = SimpleNamespace(
        agent=None,
        confirmation_mode=None,
        security_analyzer=None,
        sandbox_base_container_image=None,
        sandbox_runtime_container_image=None,
        git_user_name=None,
        git_user_email=None,
        max_iterations=None,
        max_budget_per_task=None,
        search_api_key=None,
        sandbox_api_key=None,
        mcp_config=None,
        enable_default_condenser=False,
    )

    # make start raise the desired exception
    async def start_raise(**kwargs):
        raise exc

    dummy.agent_session.start_impl = lambda *a, **k: start_raise(**k)

    # Execute
    await session_mod.WebSession.initialize_agent(dummy, settings, initial_message=None, replay_json=None)

    # Exactly one send_error call with expected contents
    assert len(dummy.send_error_calls) == 1
    assert expected_msg in dummy.send_error_calls[0]
