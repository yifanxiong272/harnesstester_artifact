import pytest
import importlib

# Import the module under test and prepare to monkeypatch module-level collaborators
import browser_use.agent.service as service


def _setup_minimal_environment():
    """Patch service module with minimal fake collaborators so Agent.__init__ can run deterministically.
    This intentionally replaces heavier dependencies and side-effectful setup with light-weight fakes.
    """

    # Deterministic uuid generator
    service.uuid7str = lambda: "00000000-0000"

    # Fake default browser profile used by DEFAULT_BROWSER_PROFILE
    class FakeProfile:
        def __init__(self, demo_mode=False, headless=False, allowed_domains=None, downloads_path=None):
            self.demo_mode = demo_mode
            self.headless = headless
            self.allowed_domains = allowed_domains or []
            self.downloads_path = downloads_path

        def model_copy(self, update=None):
            # Return a shallow copy with optional updates
            cfg = {
                'demo_mode': self.demo_mode,
                'headless': self.headless,
                'allowed_domains': list(self.allowed_domains),
                'downloads_path': self.downloads_path,
            }
            if update:
                cfg.update(update)
            return FakeProfile(**cfg)

    service.DEFAULT_BROWSER_PROFILE = FakeProfile()

    # Fake BrowserSession
    class FakeBrowserSession:
        def __init__(self, browser_profile=None, id=None):
            self.browser_profile = browser_profile or FakeProfile()
            self.id = id or "sess-000"
            self.llm_screenshot_size = None

    service.BrowserSession = FakeBrowserSession
    service.BrowserProfile = FakeProfile

    # Fake minimal LLM
    class FakeLLM:
        def __init__(self, provider='fake', model='fake-model'):
            self.provider = provider
            self.model = model

    service.BaseChatModel = FakeLLM

    # Fake Tools used in __init__ (minimal API used by Agent.__init__)
    class FakeTools:
        def __init__(self, exclude_actions=None, display_files_in_done_text=True):
            self._exclude = list(exclude_actions or [])
            self._coordinate_clicking = False

        def exclude_action(self, name):
            if name not in self._exclude:
                self._exclude.append(name)

        def set_coordinate_clicking(self, val: bool):
            self._coordinate_clicking = bool(val)

        def get_output_model(self):
            return None

        def use_structured_output_action(self, schema):
            # No-op
            pass

    service.Tools = FakeTools

    # Fake TokenCost used in __init__
    class FakeTokenCost:
        def __init__(self, include_cost=False, pricing_url=None):
            self.include_cost = include_cost
            self.pricing_url = pricing_url
            self._registered = []

        def register_llm(self, llm):
            self._registered.append((llm.provider, getattr(llm, 'model', None)))

    service.TokenCost = FakeTokenCost

    # Minimal MessageCompactionSettings
    class FakeMessageCompactionSettings:
        def __init__(self, enabled=True, compaction_llm=None):
            self.enabled = enabled
            self.compaction_llm = compaction_llm

    service.MessageCompactionSettings = FakeMessageCompactionSettings

    # Minimal AgentSettings storing a few flags accessed later
    class FakeAgentSettings:
        def __init__(self, **kwargs):
            # store requested attributes relevant for assertions
            self.message_compaction = kwargs.get('message_compaction')
            self.page_extraction_llm = kwargs.get('page_extraction_llm')
            self.use_vision = kwargs.get('use_vision')
            self.max_actions_per_step = kwargs.get('max_actions_per_step')
            self.vision_detail_level = kwargs.get('vision_detail_level')
            self.include_attributes = kwargs.get('include_attributes')
            self.max_history_items = kwargs.get('max_history_items')
            self.max_clickable_elements_length = kwargs.get('max_clickable_elements_length')
            # explicit values we assert
            self.flash_mode = kwargs.get('flash_mode')
            self.enable_planning = kwargs.get('enable_planning')
            self.llm_timeout = kwargs.get('llm_timeout')
            self.loop_detection_window = kwargs.get('loop_detection_window')

    service.AgentSettings = FakeAgentSettings

    # Minimal AgentState and AgentHistoryList used in __init__
    class FakeLoopDetector:
        def __init__(self):
            self.window_size = None

    class FakeAgentState:
        def __init__(self):
            self.message_manager_state = {}
            self.loop_detector = FakeLoopDetector()

    service.AgentState = FakeAgentState

    class FakeAgentHistoryList:
        def __init__(self, history=None, usage=None):
            self.history = history or []
            self.usage = usage

    service.AgentHistoryList = FakeAgentHistoryList

    # Fake SystemPrompt and MessageManager used to avoid constructing heavy objects
    class FakeSystemPrompt:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def get_system_message(self):
            return "<system>"

    class FakeMessageManager:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    service.SystemPrompt = FakeSystemPrompt
    service.MessageManager = FakeMessageManager

    # Replace methods on Agent that perform external setup to no-ops
    # (filesystem, screenshot service, action models, & telemetry/version checks)
    def _noop_set_file_system(self, file_system_path):
        # Ensure attribute expected later exists
        self.file_system = None

    def _noop_set_screenshot_service(self):
        self._screenshot_service = None

    def _noop_setup_action_models(self):
        self._actions_setup = True

    def _noop_set_version_and_source(self, source):
        self._version_source = source

    service.Agent._set_file_system = _noop_set_file_system
    service.Agent._set_screenshot_service = _noop_set_screenshot_service
    service.Agent._setup_action_models = _noop_setup_action_models
    service.Agent._set_browser_use_version_and_source = _noop_set_version_and_source

    # Minimal EventBus and telemetry replacements
    class FakeEventBus:
        def __init__(self, name=None):
            self.name = name

    service.EventBus = FakeEventBus
    service.ProductTelemetry = lambda: object()

    # Ensure CONFIG exists and has DEFAULT_LLM attribute for safety
    class FakeConfig:
        def __init__(self):
            self.DEFAULT_LLM = None

    service.CONFIG = getattr(service, 'CONFIG', FakeConfig())


def _make_fake_llm(provider='fake', model='fake-model'):
    # A small helper to create an LLM-like object used by Agent
    class _LLM:
        def __init__(self, provider, model):
            self.provider = provider
            self.model = model

    return _LLM(provider, model)


def test_llm_screenshot_size_validation_round_033():
    _setup_minimal_environment()

    # 1) Wrong length should raise a clear ValueError
    with pytest.raises(ValueError) as excinfo_len:
        service.Agent(task="t1", llm=_make_fake_llm(), llm_screenshot_size=(100,))
    assert "llm_screenshot_size must be a tuple of (width, height)" in str(excinfo_len.value)

    # 2) Wrong element types should raise a different clear ValueError
    with pytest.raises(ValueError) as excinfo_type:
        service.Agent(task="t2", llm=_make_fake_llm(), llm_screenshot_size=(100, "200"))
    assert "dimensions must be integers" in str(excinfo_type.value)


def test_auto_config_and_flash_mode_round_033():
    _setup_minimal_environment()

    # Auto-configure llm_screenshot_size for claude-sonnet family when None
    llm_claude = _make_fake_llm(provider='anthropic', model='anthropic/claude-sonnet-4-6')
    agent_claude = service.Agent(task="t-claude", llm=llm_claude, llm_screenshot_size=None)

    # Browser session should receive the auto-configured screenshot size
    assert getattr(agent_claude.browser_session, 'llm_screenshot_size', None) == (1400, 850)

    # When LLM provider is 'browser-use' flash_mode should be set True and planning disabled
    llm_browser_use = _make_fake_llm(provider='browser-use', model='browser-use/special-model')
    # explicitly pass flash_mode False to ensure code flips it based on provider
    agent_flash = service.Agent(task="t-flash", llm=llm_browser_use, flash_mode=False)
    assert agent_flash.settings.flash_mode is True
    # enable_planning should be False because flash_mode strips planning capability
    assert agent_flash.settings.enable_planning is False


def test_browser_and_skills_conflicts_round_033():
    _setup_minimal_environment()

    # Both browser and browser_session specified should raise a ValueError
    fake_browser = object()
    fake_browser_session = object()
    with pytest.raises(ValueError) as excinfo_browser:
        service.Agent(task="t-conflict", llm=_make_fake_llm(), browser=fake_browser, browser_session=fake_browser_session)
    assert 'Cannot specify both "browser" and "browser_session"' in str(excinfo_browser.value)

    # Both skills and skill_ids specified should raise a ValueError
    with pytest.raises(ValueError) as excinfo_skills:
        service.Agent(task="t-skills", llm=_make_fake_llm(), skills=['a'], skill_ids=['b'])
    assert 'Cannot specify both "skills" and "skill_ids"' in str(excinfo_skills.value)
