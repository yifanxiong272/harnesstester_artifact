import importlib
import pytest

# Load the module under test
svc = importlib.import_module('browser_use.beta.service')

# Lightweight stubs and helpers to avoid heavy imports, network, or filesystem access.
class SimpleLLM:
    def __init__(self, provider=None, model='test-model'):
        self.provider = provider
        self.model = model

class DummySystemPrompt:
    def __init__(self, *args, **kwargs):
        # Accept any constructor signature used by Agent.__init__
        pass

    def get_system_message(self):
        return 'SYSTEM'

class DummyMessageManager:
    def __init__(self, *args, **kwargs):
        # capture the llm_screenshot_size and other important kwargs for inspection
        self._init_args = args
        self._init_kwargs = kwargs

class DummyTokenCost:
    def __init__(self, include_cost=False, pricing_url=None):
        self.include_cost = include_cost
        self.pricing_url = pricing_url

class DummyEventBus:
    def __init__(self, name=None):
        self.name = name

# Patch module-level collaborators to deterministic stubs
svc.SystemPrompt = DummySystemPrompt
svc.MessageManager = DummyMessageManager
svc.TokenCost = DummyTokenCost
svc.ProductTelemetry = lambda: object()
svc.EventBus = DummyEventBus
svc._register_llm_for_usage = lambda token_cost_service, llm: None
svc.uuid7str = lambda: 'fixed-uuid-7'
svc._default_browser_session = lambda agent_id, browser_profile, browser_session, browser: (None, None)
svc._resolve_default_llm = lambda llm: llm or SimpleLLM()
svc._resolve_tools = lambda *args, **kwargs: {}
# Make browser profile/domain extraction helpers deterministic
svc._extract_profile_domains = lambda browser_session, browser_profile, attr: []
svc._managed_browser_launch_args = lambda a, b: []
svc._managed_browser_profile_dir = lambda a, b: None
svc._managed_browser_executable_path = lambda a, b: None
svc._managed_browser_env = lambda a, b: {}
svc._extract_cdp_headers = lambda a, b: {}
svc._extract_user_agent = lambda a, b: None
svc._extract_highlight_settings = lambda a, b: (False, None, None)
svc._extract_wait_timing_settings = lambda a, b: {}
svc._extract_block_ip_addresses = lambda a, b: []
svc._extract_profile_permissions = lambda a, b: {}
svc._extract_browser_downloads = lambda a, b: (False, None)
svc._extract_browser_viewport = lambda a, b: (False, None)
svc._extract_browser_window_size = lambda a, b: None
svc._extract_browser_storage_state = lambda a, b: None
svc._sensitive_data_context = lambda sensitive_data: {}
svc._warn_sensitive_data_domain_constraints = lambda logger, sensitive_data, allowed_domains: None

# Avoid doing filesystem and screenshot service setup inside Agent
svc.Agent._set_file_system = lambda self, path: None
svc.Agent._set_screenshot_service = lambda self: None

# Tests
@pytest.mark.parametrize(
    'value,expected_message',
    [
        ((10,), 'llm_screenshot_size must be a tuple of (width, height)'),
        ((100.0, 200.0), 'llm_screenshot_size dimensions must be integers'),
        ((50, 150), 'llm_screenshot_size dimensions must be at least 100 pixels'),
    ],
)
def test_llm_screenshot_size_validation_round_089(value, expected_message):
    """
    Exercise the llm_screenshot_size validation branches that raise ValueError.
    - tuple length != 2
    - non-int dimensions
    - dimension less than allowed minimum (100)
    """
    llm = SimpleLLM(provider=None, model='some-model')
    with pytest.raises(ValueError) as ei:
        svc.Agent(task='t', llm=llm, llm_screenshot_size=value)
    assert expected_message in str(ei.value)


def test_claude_sonnet_and_extraction_schema_round_089(monkeypatch):
    """
    When llm.model indicates a claude-sonnet model (with a provider prefix),
    llm_screenshot_size should be auto-configured to (1400, 850).
    Also verify extraction_schema is derived from the provided output_model_schema.
    """
    # Ensure deterministic helpers for this test
    monkeypatch.setattr(svc, 'uuid7str', lambda: 'fixed-uuid')
    monkeypatch.setattr(svc, '_resolve_default_llm', lambda llm: llm)
    monkeypatch.setattr(svc, '_default_browser_session', lambda *a, **k: (None, None))

    # Provide an LLM whose model ends with 'claude-sonnet-...' and no explicit llm_screenshot_size
    llm = SimpleLLM(provider='anthropic', model='anthropic/claude-sonnet-4-6')

    # Provide a fake output_model_schema class with model_json_schema()
    class DummyOutputSchema:
        @staticmethod
        def model_json_schema():
            return {'dummy': 'schema'}

    # Pass message_compaction as False to avoid MessageCompactionSettings conversion
    agent = svc.Agent(
        task='task-url-or-text',
        llm=llm,
        llm_screenshot_size=None,
        output_model_schema=DummyOutputSchema,
        message_compaction=False,
        page_extraction_llm=None,
        fallback_llm=None,
        judge_llm=None,
        calculate_cost=False,
    )

    # The patched MessageManager stored its received kwargs; retrieve that instance via agent
    mm = agent._message_manager
    # MessageManager was replaced with DummyMessageManager, which stores kwargs
    assert isinstance(mm, DummyMessageManager)
    # The Agent should have resulted in llm_screenshot_size being set to (1400, 850) and passed
    passed_llm_screenshot_size = mm._init_kwargs.get('llm_screenshot_size')
    assert passed_llm_screenshot_size == (1400, 850)

    # extraction_schema should be created from DummyOutputSchema.model_json_schema()
    assert agent.extraction_schema == {'dummy': 'schema'}
    # The original llm should be preserved on the agent
    assert agent.llm is llm


def test_skills_conflict_and_skill_service_assignment_round_089(monkeypatch):
    """
    - Verify that specifying both skills and skill_ids raises a ValueError.
    - Verify that providing an explicit skill_service sets the attribute directly.
    """
    # Basic deterministic helpers
    monkeypatch.setattr(svc, 'uuid7str', lambda: 'fixed-uuid')
    monkeypatch.setattr(svc, '_resolve_default_llm', lambda llm: llm or SimpleLLM())
    monkeypatch.setattr(svc, '_default_browser_session', lambda *a, **k: (None, None))
    monkeypatch.setattr(svc, 'MessageManager', DummyMessageManager)

    llm = SimpleLLM()

    # Conflict case: both skills and skill_ids provided -> should raise ValueError
    with pytest.raises(ValueError) as ei:
        svc.Agent(task='t', llm=llm, skills=['s'], skill_ids=['i'])
    assert 'Cannot specify both "skills" and "skill_ids"' in str(ei.value)

    # skill_service assignment: agent.skill_service should equal provided object
    my_skill_service = object()
    agent = svc.Agent(task='t', llm=llm, skill_service=my_skill_service, message_compaction=False)
    assert agent.skill_service is my_skill_service
