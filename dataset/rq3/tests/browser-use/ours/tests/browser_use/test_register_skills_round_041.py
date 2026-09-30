import asyncio
import types
import pytest

import browser_use.agent.service as service_mod

# Helper test fixtures / fakes used across tests
class DummyLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []

    def info(self, *args, **kwargs):
        self.infos.append(args[0] if args else '')

    def warning(self, *args, **kwargs):
        self.warnings.append(args[0] if args else '')

class FakeActionResult:
    def __init__(self, extracted_content=None, error=None):
        self.extracted_content = extracted_content
        self.error = error

class FakeBaseModel:
    """Stand-in for pydantic.BaseModel used by the code under test."""
    def __init__(self, dump_value=None):
        # dump_value used by model_dump() to simulate different scenarios
        self._dump_value = dump_value or {}

    def model_dump(self):
        return self._dump_value

class FakeSkill:
    def __init__(self, id_, title, description, param_model):
        self.id = id_
        self.title = title
        self.description = description
        self._param_model = param_model

    def parameters_pydantic(self, exclude_cookies=True):
        return self._param_model

class FakeResult:
    def __init__(self, success: bool, result=None, error=None):
        self.success = success
        self.result = result
        self.error = error

class Registry:
    def __init__(self):
        self.registered = []

    def action(self, description=None, param_model=None):
        # Return a decorator that captures the handler
        def decorator(func):
            self.registered.append({
                'name': getattr(func, '__name__', None),
                'func': func,
                'description': description,
                'param_model': param_model,
            })
            return func
        return decorator

class FakeTools:
    def __init__(self):
        self.registry = Registry()

class FakeBrowserSession:
    def __init__(self, cookies_value=None):
        self._cookies_value = cookies_value or {"cookie": "v"}

    async def cookies(self):
        return self._cookies_value

class FakeSkillService:
    def __init__(self, skills, behavior_map=None):
        # skills: list of FakeSkill
        self._skills = skills
        # behavior_map: dict mapping scenario -> action
        # execute_skill will inspect parameters to find scenario key
        self._behavior_map = behavior_map or {}

    async def get_all_skills(self):
        return self._skills

    async def execute_skill(self, skill_id, parameters, cookies):
        # parameters should be a dict (already converted by handler)
        scenario = None
        if isinstance(parameters, dict):
            scenario = parameters.get('scenario')
        # Lookup behavior
        behavior = self._behavior_map.get(scenario)
        if callable(behavior):
            return behavior(skill_id, parameters, cookies)
        # If behavior is an exception to raise
        if isinstance(behavior, Exception):
            raise behavior
        # default: success echo
        return FakeResult(success=True, result={'skill_id': skill_id, 'params': parameters})

# Helper to bind and call the async method under test
async def _call_register(fake_self):
    bound = service_mod.Agent._register_skills_as_actions.__get__(fake_self, service_mod.Agent)
    return await bound()

@pytest.mark.asyncio
async def test_no_skill_service_round_041(monkeypatch):
    """If skill_service is None the method returns early and does not mark skills registered."""
    # Arrange
    fake_self = types.SimpleNamespace()
    fake_self.skill_service = None
    fake_self._skills_registered = False
    fake_self.logger = DummyLogger()

    # Act
    await _call_register(fake_self)

    # Assert: still not registered and no info log about registering
    assert fake_self._skills_registered is False
    # No 'Registering skill actions...' info logged
    assert not any('Registering skill actions' in i for i in fake_self.logger.infos)

@pytest.mark.asyncio
async def test_no_skills_loaded_round_041(monkeypatch):
    """If skill_service.get_all_skills returns empty list, the method warns and returns."""
    # Arrange
    fake_self = types.SimpleNamespace()
    fake_self.skill_service = types.SimpleNamespace()
    async def gs():
        return []
    fake_self.skill_service.get_all_skills = gs
    fake_self._skills_registered = False
    fake_self.logger = DummyLogger()

    # Act
    await _call_register(fake_self)

    # Assert
    assert fake_self._skills_registered is False
    assert any('No skills loaded from SkillService' in w for w in fake_self.logger.warnings)

@pytest.mark.asyncio
async def test_skill_handler_various_paths_round_041(monkeypatch):
    """Register a single skill and exercise the handler across parameter types and exceptions.

    This test patches ActionResult and BaseModel inside the module and uses a controllable
    FakeSkillService.execute_skill behavior map to force the branches exercised.
    """
    # Patch module-level ActionResult and BaseModel to our fakes so isinstance checks and return types work
    monkeypatch.setattr(service_mod, 'ActionResult', FakeActionResult)
    monkeypatch.setattr(service_mod, 'BaseModel', FakeBaseModel)

    # Prepare fake skill and behavior mapping
    def behavior_success(skill_id, params, cookies):
        return FakeResult(success=True, result='OK-'+str(params.get('scenario')))

    def behavior_failure(skill_id, params, cookies):
        return FakeResult(success=False, result=None, error='failed-exec')

    class MissingCookieExc(Exception):
        pass

    # Make instance that will be raised with expected attributes
    missing_exc = MissingCookieExc('cookie missing')
    # emulate attributes the code checks
    setattr(missing_exc, 'cookie_name', 'sessionid')
    setattr(missing_exc, 'cookie_description', 'session cookie required')

    def behavior_raise_missing(skill_id, params, cookies):
        raise missing_exc

    def behavior_raise_generic(skill_id, params, cookies):
        raise ValueError('boom')

    behavior_map = {
        'success': behavior_success,
        'failure': behavior_failure,
        'raise_missing': behavior_raise_missing,
        'raise_generic': behavior_raise_generic,
        # default if no scenario: success
    }

    # Create skill and skill service
    param_model = object()  # param_model passed to action decorator, not inspected by our test
    skill = FakeSkill(id_='skill-1', title='T', description='Desc', param_model=param_model)
    fake_skill_service = FakeSkillService([skill], behavior_map=behavior_map)

    # Prepare fake self
    fake_self = types.SimpleNamespace()
    fake_self.skill_service = fake_skill_service
    fake_self._skills_registered = False
    fake_self.logger = DummyLogger()
    fake_self.browser_session = FakeBrowserSession(cookies_value={'k': 'v'})
    fake_self.tools = FakeTools()
    # _get_skill_slug should be callable
    fake_self._get_skill_slug = lambda s, all_s: 'skill_slug'

    # initial_actions branch: provide one action with model_dump and a _convert_initial_actions implementation
    class FakeAction:
        def model_dump(self, exclude_unset=True):
            return {'from': 'action'}

    converted_marker = ['converted-action']
    fake_self.initial_actions = [FakeAction()]
    fake_self._convert_initial_actions = lambda d: converted_marker

    # Make sure _setup_action_models exists (no-op)
    fake_self._setup_action_models = lambda: None

    # Run registration
    await _call_register(fake_self)

    # After registration, one handler should be registered
    reg = fake_self.tools.registry.registered
    assert len(reg) == 1
    handler_entry = reg[0]
    handler = handler_entry['func']
    # Handler __name__ should be set to slug in registration code
    assert handler_entry['name'] == 'skill_slug'

    # Test 1: dict params -> success
    res = await handler({'scenario': 'success'})
    assert isinstance(res, FakeActionResult)
    assert res.extracted_content == 'OK-success'
    assert res.error is None

    # Test 2: dict params -> failure result from skill_service
    res2 = await handler({'scenario': 'failure'})
    assert isinstance(res2, FakeActionResult)
    assert res2.extracted_content is None
    assert res2.error == 'failed-exec'

    # Test 3: raises MissingCookieException -> formatted missing cookie message
    res3 = await handler({'scenario': 'raise_missing'})
    assert isinstance(res3, FakeActionResult)
    assert res3.extracted_content is None
    assert 'Missing cookies (sessionid): session cookie required' == res3.error

    # Test 4: raises generic -> generic error message format contains exception name
    res4 = await handler({'scenario': 'raise_generic'})
    assert isinstance(res4, FakeActionResult)
    assert res4.extracted_content is None
    assert 'Skill execution error' in res4.error
    assert 'ValueError' in res4.error

    # Test 5: invalid params type (not BaseModel or dict) -> returns invalid parameters type error
    res5 = await handler(123)
    assert isinstance(res5, FakeActionResult)
    assert res5.extracted_content is None
    assert 'Invalid parameters type' in res5.error

    # Test 6: BaseModel instance path: should call model_dump and succeed
    bm = FakeBaseModel(dump_value={'scenario': 'success'})
    res6 = await handler(bm)
    assert isinstance(res6, FakeActionResult)
    assert res6.extracted_content == 'OK-success'
    assert res6.error is None

    # Verify initial_actions was converted using our _convert_initial_actions
    assert fake_self.initial_actions is converted_marker

    # Verify that final info log includes the Registered message with the number of skills
    assert any('Registered 1 skill actions' in i for i in fake_self.logger.infos)
