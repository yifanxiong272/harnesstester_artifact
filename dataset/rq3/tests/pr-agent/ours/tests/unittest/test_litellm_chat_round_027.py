import asyncio
import types
import json
import importlib
import pytest

module = importlib.import_module('pr_agent.algo.ai_handlers.litellm_ai_handler')
from pr_agent.algo.ai_handlers.litellm_ai_handler import LiteLLMAIHandler


class FakeLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []
        self.errors = []
        self.debugs = []

    def info(self, *args, **kwargs):
        self.infos.append((args, kwargs))

    def warning(self, *args, **kwargs):
        self.warnings.append((args, kwargs))

    def error(self, *args, **kwargs):
        self.errors.append((args, kwargs))

    def debug(self, *args, **kwargs):
        self.debugs.append((args, kwargs))


class FakeSettingsConfig:
    def __init__(self, reasoning_effort=None, custom_reasoning_model=False, ai_timeout=10, verbosity_level=1, seed=-1):
        self.reasoning_effort = reasoning_effort
        self.custom_reasoning_model = custom_reasoning_model
        self.ai_timeout = ai_timeout
        self.verbosity_level = verbosity_level
        self.seed = seed


class FakeSettings:
    def __init__(self, config=None, litellm_dict=None, get_map=None):
        self.config = config or FakeSettingsConfig()
        # provide litellm as an object with attribute "extra_headers" when needed
        self.litellm = types.SimpleNamespace(**(litellm_dict or {}))
        self._get_map = get_map or {}

    def get(self, key, default=None):
        return self._get_map.get(key, default)


# A fake ReasoningEffort that is callable (constructor) and iterable for the list comprehension in code
class FakeReasoningEffort:
    class Item:
        def __init__(self, value):
            self.value = value

    MEDIUM = Item('MEDIUM_DEFAULT')

    def __init__(self, val=None):
        # raise for an explicitly invalid sentinel to simulate invalid config
        if val == 'INVALID_SENTINEL':
            raise ValueError('invalid')
        # otherwise succeed

    @classmethod
    def __iter__(cls):
        # provide at least one element with .value for the list comprehension
        yield cls.MEDIUM


@pytest.mark.asyncio
async def test_img_path_not_alive_round_027(monkeypatch):
    """
    Ensure that if requests.head returns 404 the function returns the specific error tuple.
    Covers branches around the img_path HEAD 404 early return.
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(module, 'get_logger', lambda: fake_logger)

    # minimal fake settings
    fake_settings = FakeSettings()
    monkeypatch.setattr(module, 'get_settings', lambda: fake_settings)

    # Make requests.head return an object with status_code 404
    class Resp404:
        status_code = 404

    monkeypatch.setattr(module.requests, 'head', lambda url, allow_redirects=True: Resp404())

    # Create a dummy "self" with required attributes and async _get_completion (should not be reached)
    async def _get_completion(**kwargs):
        return ("SHOULD_NOT_BE_CALLED", None, {})

    dummy = types.SimpleNamespace(
        _aws_imds_mode=False,
        _aws_imds_fell_back=False,
        _aws_static_creds=False,
        _refresh_aws_imds_credentials=lambda: True,
        _activate_static_aws_fallback=lambda: None,
        _aws_bedrock_lock=None,
        deployment_id='dep',
        azure=False,
        user_message_only_models=[],
        api_base='https://api',
        no_support_temperature_models=[],
        support_reasoning_models=[],
        claude_extended_thinking_models=[],
        repetition_penalty=None,
        _get_completion=_get_completion,
    )

    resp, reason = await module.LiteLLMAIHandler.chat_completion(dummy, model='openai/test', system='sys', user='u', temperature=0.2, img_path='http://image')

    assert reason == 'error'
    assert 'The image link is not' in resp
    # ensure logger recorded an error about image link
    assert any('image link' in str(args) or 'image link' in str(kwargs) for args, kwargs in fake_logger.errors)


@pytest.mark.asyncio
async def test_img_path_fetch_exception_round_027(monkeypatch):
    """
    If requests.head raises an exception, chat_completion should return the Error fetching image tuple.
    Covers exception path in image checking.
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(module, 'get_logger', lambda: fake_logger)
    monkeypatch.setattr(module, 'get_settings', lambda: FakeSettings())

    def raise_exc(url, allow_redirects=True):
        raise RuntimeError('boom')

    monkeypatch.setattr(module.requests, 'head', raise_exc)

    async def _get_completion(**kwargs):
        return ("SHOULD_NOT_BE_CALLED", None, {})

    dummy = types.SimpleNamespace(
        _aws_imds_mode=False,
        _aws_imds_fell_back=False,
        _aws_static_creds=False,
        _refresh_aws_imds_credentials=lambda: True,
        _activate_static_aws_fallback=lambda: None,
        _aws_bedrock_lock=None,
        deployment_id='dep',
        azure=False,
        user_message_only_models=[],
        api_base='https://api',
        no_support_temperature_models=[],
        support_reasoning_models=[],
        claude_extended_thinking_models=[],
        repetition_penalty=None,
        _get_completion=_get_completion,
    )

    resp, reason = await module.LiteLLMAIHandler.chat_completion(dummy, model='openai/test', system='sys', user='u', temperature=0.2, img_path='http://image')

    assert reason == 'error'
    assert 'Error fetching image' in resp
    # ensure logger.error captured exception context
    assert fake_logger.errors


@pytest.mark.asyncio
async def test_claude_empty_system_round_027(monkeypatch):
    """
    If model contains 'claude' and system is empty, a default system prompt should be added and a warning logged.
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(module, 'get_logger', lambda: fake_logger)

    # settings default
    monkeypatch.setattr(module, 'get_settings', lambda: FakeSettings())

    # Ensure requests.head is not invoked
    monkeypatch.setattr(module.requests, 'head', lambda *args, **kwargs: None)

    captured = {}

    async def _get_completion(**kwargs):
        # capture kwargs to inspect
        captured['kwargs'] = kwargs
        return ("the-reply", "stop", {})

    dummy = types.SimpleNamespace(
        _aws_imds_mode=False,
        _aws_imds_fell_back=False,
        _aws_static_creds=False,
        _refresh_aws_imds_credentials=lambda: True,
        _activate_static_aws_fallback=lambda: None,
        _aws_bedrock_lock=None,
        deployment_id='dep',
        azure=False,
        user_message_only_models=[],
        api_base='https://api',
        no_support_temperature_models=[],
        support_reasoning_models=[],
        claude_extended_thinking_models=[],
        repetition_penalty=None,
        _get_completion=_get_completion,
    )

    resp, reason = await module.LiteLLMAIHandler.chat_completion(dummy, model='claude-internal', system='', user='U', temperature=0.0, img_path=None)

    assert resp == 'the-reply'
    assert reason == 'stop'
    # verify the warning about empty system prompt was logged
    assert any('Empty system prompt' in str(args) for args, kwargs in fake_logger.warnings)


@pytest.mark.asyncio
async def test_gpt5_thinking_round_027(monkeypatch):
    """
    For models starting with 'gpt-5', invalid reasoning_effort should trigger fallback and removal of temperature from kwargs.
    This covers the gpt-5 validation, fallback, and thinking_kwargs handling.
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(module, 'get_logger', lambda: fake_logger)

    # Provide settings where reasoning_effort is invalid (we use sentinel that FakeReasoningEffort will raise on)
    fake_config = FakeSettingsConfig(reasoning_effort='INVALID_SENTINEL', custom_reasoning_model=False, ai_timeout=5, verbosity_level=1, seed=-1)
    fake_settings = FakeSettings(config=fake_config, litellm_dict={'extra_headers': '{}'}, get_map={})
    monkeypatch.setattr(module, 'get_settings', lambda: fake_settings)

    # Patch ReasoningEffort in module to our fake one which raises for 'INVALID_SENTINEL'
    monkeypatch.setattr(module, 'ReasoningEffort', FakeReasoningEffort)

    # ensure _process_litellm_extra_body is identity
    monkeypatch.setattr(module, '_process_litellm_extra_body', lambda kwargs: kwargs)

    captured = {}

    async def _get_completion(**kwargs):
        captured.update(kwargs)
        return ('gpt5-reply', 'end', {})

    dummy = types.SimpleNamespace(
        _aws_imds_mode=False,
        _aws_imds_fell_back=False,
        _aws_static_creds=False,
        _refresh_aws_imds_credentials=lambda: True,
        _activate_static_aws_fallback=lambda: None,
        _aws_bedrock_lock=None,
        deployment_id='dep',
        azure=False,
        user_message_only_models=[],
        api_base='https://api',
        no_support_temperature_models=[],
        support_reasoning_models=[],
        claude_extended_thinking_models=[],
        repetition_penalty=None,
        _get_completion=_get_completion,
    )

    # Call with a temperature that would ordinarily be added then removed by thinking kwargs
    resp, reason = await module.LiteLLMAIHandler.chat_completion(dummy, model='gpt-5_thinking', system='S', user='U', temperature=0.3, img_path=None)

    assert resp == 'gpt5-reply'
    assert reason == 'end'
    # Ensure temperature was removed by thinking_kwargs logic
    assert 'temperature' not in captured
    # The fallback reasoning_effort should be present and equal to FakeReasoningEffort.MEDIUM.value
    assert captured.get('reasoning_effort') == FakeReasoningEffort.MEDIUM.value
    # The logger should have a warning about invalid reasoning_effort
    assert any('Invalid reasoning_effort' in str(args) or 'Invalid reasoning_effort' in str(kwargs) for args, kwargs in fake_logger.warnings)


def test_invalid_litellm_extra_headers_round_027(monkeypatch):
    """
    If litellm.extra_headers contains invalid JSON and get_settings().get indicates EXTRA_HEADERS are enabled,
    chat_completion should raise a ValueError about invalid JSON.
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(module, 'get_logger', lambda: fake_logger)

    # settings with litellm.extra_headers invalid JSON string and get() returning True for LITELLM.EXTRA_HEADERS
    conf = FakeSettingsConfig()
    fake_settings = FakeSettings(config=conf, litellm_dict={'extra_headers': 'not-json'}, get_map={"LITELLM.EXTRA_HEADERS": True})
    monkeypatch.setattr(module, 'get_settings', lambda: fake_settings)

    # patch requests.head to avoid image logic
    monkeypatch.setattr(module.requests, 'head', lambda *args, **kwargs: None)

    async def caller():
        async def _get_completion(**kwargs):
            return ('x', None, {})

        dummy = types.SimpleNamespace(
            _aws_imds_mode=False,
            _aws_imds_fell_back=False,
            _aws_static_creds=False,
            _refresh_aws_imds_credentials=lambda: True,
            _activate_static_aws_fallback=lambda: None,
            _aws_bedrock_lock=None,
            deployment_id='dep',
            azure=False,
            user_message_only_models=[],
            api_base='https://api',
            no_support_temperature_models=[],
            support_reasoning_models=[],
            claude_extended_thinking_models=[],
            repetition_penalty=None,
            _get_completion=_get_completion,
        )

        # Call should raise ValueError when parsing extra_headers
        await module.LiteLLMAIHandler.chat_completion(dummy, model='openai/test', system='s', user='u', temperature=0.0, img_path=None)

    with pytest.raises(ValueError) as exc:
        asyncio.get_event_loop().run_until_complete(caller())

    assert 'LITELLM.EXTRA_HEADERS contains invalid JSON' in str(exc.value)
