import types
import asyncio
import logging
from types import SimpleNamespace
import builtins

import pytest

from gpt_researcher.utils import llm as llm_module
from gpt_researcher.utils.llm import construct_subtopics


# Helper factories to create fake PromptTemplate / Parser / get_llm per-test
def _make_prompt_template_factory(output=None, raise_exc=False):
    class FakePromptTemplate:
        def __init__(self, template, input_variables, partial_variables):
            # store args for potential debugging
            self.template = template
            self.input_variables = input_variables
            self.partial_variables = partial_variables

        def __or__(self, other_model):
            prompt = self
            model = other_model

            class Intermediate:
                def __init__(self, prompt, model):
                    self.prompt = prompt
                    self.model = model

                def __or__(self, parser):
                    class Chain:
                        async def ainvoke(self, inputs, **kwargs):
                            if raise_exc:
                                raise RuntimeError("simulated chain failure")
                            # return whatever the test wants (can be any python object)
                            return output

                    return Chain()

            return Intermediate(prompt, model)

    return FakePromptTemplate


class FakePydanticOutputParser:
    def __init__(self, pydantic_object=None):
        # accept the pydantic_object argument but do nothing with it
        self.pydantic_object = pydantic_object

    def get_format_instructions(self):
        return "<FORMAT_INSTRUCTIONS>"


def _make_fake_get_llm(capture_dict, expected_assertion=None, provider_return_llm=None):
    def fake_get_llm(llm_provider, **provider_kwargs):
        # record what was passed for assertions in the test
        capture_dict['called_with'] = {'llm_provider': llm_provider, 'provider_kwargs': dict(provider_kwargs)}
        if expected_assertion is not None:
            expected_assertion(provider_kwargs)
        # return a simple provider with an .llm attribute (actual value not used by FakePromptTemplate)
        return SimpleNamespace(llm=provider_return_llm if provider_return_llm is not None else object())

    return fake_get_llm


def _make_prompt_family():
    class PF:
        def generate_subtopics_prompt(self):
            return "generate subtopics prompt"

    return PF()


def _make_config(**overrides):
    # config must provide attributes referenced in construct_subtopics
    defaults = {
        'smart_llm_model': 'default-model',
        'llm_kwargs': None,
        'temperature': 0.7,
        'smart_token_limit': 256,
        'smart_llm_provider': 'fake-provider',
        'max_subtopics': 5,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_construct_subtopics_reasoning_round_062(monkeypatch):
    """
    Cover branch where config.llm_kwargs is truthy (update path) and
    smart_llm_model is in SUPPORT_REASONING_EFFORT_MODELS so reasoning_effort is set.
    """
    # Prepare capture dicts
    capture = {}

    # Patch PydanticOutputParser and PromptTemplate in the module under test
    monkeypatch.setattr(llm_module, 'PydanticOutputParser', FakePydanticOutputParser)

    expected_output = ['subtopic-a', 'subtopic-b']
    FakePromptTemplate = _make_prompt_template_factory(output=expected_output, raise_exc=False)
    monkeypatch.setattr(llm_module, 'PromptTemplate', FakePromptTemplate)

    # Ensure SUPPORT_REASONING_EFFORT_MODELS contains our test model
    monkeypatch.setattr(llm_module, 'SUPPORT_REASONING_EFFORT_MODELS', { 'model-with-reasoning' })

    # Provide a ReasoningEfforts where High.value is a sentinel
    class _RE:
        class High:
            value = 'HIGH_SENTINEL'
    monkeypatch.setattr(llm_module, 'ReasoningEfforts', _RE)

    # make get_llm assert that reasoning_effort key is present and llm_kwargs merged
    def assert_provider_kwargs(provider_kwargs):
        # provider_kwargs must include merged llm_kwargs and reasoning_effort
        assert provider_kwargs.get('reasoning_effort') == 'HIGH_SENTINEL'
        assert provider_kwargs.get('model') == 'model-with-reasoning'
        # llm_kwargs keys should be preserved
        assert provider_kwargs.get('some_custom') == 'yes'

    fake_get_llm = _make_fake_get_llm(capture, expected_assertion=assert_provider_kwargs)
    monkeypatch.setattr(llm_module, 'get_llm', fake_get_llm)

    prompt_family = _make_prompt_family()

    config = _make_config(smart_llm_model='model-with-reasoning', llm_kwargs={'some_custom': 'yes'})

    # Call the async function synchronously
    result = asyncio.run(construct_subtopics('task-x', 'data-y', config, subtopics=['existing'], prompt_family=prompt_family))

    # Assertions: the chain returned the expected output and provider was called as asserted
    assert result == expected_output
    assert 'called_with' in capture
    assert capture['called_with']['llm_provider'] == 'fake-provider'


def test_construct_subtopics_temperature_round_062(monkeypatch):
    """
    Cover branch where smart_llm_model is NOT in SUPPORT_REASONING_EFFORT_MODELS,
    so temperature and max_tokens keys are added to provider kwargs.
    Also cover branch where config.llm_kwargs is falsy (None) so no update call.
    """
    capture = {}

    monkeypatch.setattr(llm_module, 'PydanticOutputParser', FakePydanticOutputParser)

    expected_output = { 'subtopics': ['one'] }
    FakePromptTemplate = _make_prompt_template_factory(output=expected_output, raise_exc=False)
    monkeypatch.setattr(llm_module, 'PromptTemplate', FakePromptTemplate)

    # Ensure SUPPORT_REASONING_EFFORT_MODELS does NOT contain our test model
    monkeypatch.setattr(llm_module, 'SUPPORT_REASONING_EFFORT_MODELS', set())

    # Patch ReasoningEfforts to something harmless (not used in this branch)
    class _RE:
        class High:
            value = 'unused'
    monkeypatch.setattr(llm_module, 'ReasoningEfforts', _RE)

    # get_llm should receive temperature and max_tokens keys
    def assert_provider_kwargs(provider_kwargs):
        assert provider_kwargs.get('model') == 'plain-model'
        assert 'reasoning_effort' not in provider_kwargs
        assert provider_kwargs.get('temperature') == 0.42
        assert provider_kwargs.get('max_tokens') == 123

    fake_get_llm = _make_fake_get_llm(capture, expected_assertion=assert_provider_kwargs)
    monkeypatch.setattr(llm_module, 'get_llm', fake_get_llm)

    prompt_family = _make_prompt_family()

    config = _make_config(smart_llm_model='plain-model', llm_kwargs=None, temperature=0.42, smart_token_limit=123)

    result = asyncio.run(construct_subtopics('task-a', 'data-b', config, subtopics=[] , prompt_family=prompt_family))

    assert result == expected_output
    assert 'called_with' in capture
    assert capture['called_with']['llm_provider'] == 'fake-provider'


def test_construct_subtopics_exception_round_062(monkeypatch):
    """
    Simulate an exception raised by the chain. Ensure the function catches it,
    logs, and returns the original subtopics list (exception branch coverage).
    """
    capture = {}

    monkeypatch.setattr(llm_module, 'PydanticOutputParser', FakePydanticOutputParser)

    # Make the PromptTemplate chain raise when ainvoke is called
    FakePromptTemplate = _make_prompt_template_factory(output=None, raise_exc=True)
    monkeypatch.setattr(llm_module, 'PromptTemplate', FakePromptTemplate)

    # Keep SUPPORT_REASONING_EFFORT_MODELS empty so else branch won't attempt reasoning eff
    monkeypatch.setattr(llm_module, 'SUPPORT_REASONING_EFFORT_MODELS', set())

    # Patch get_llm simply to return a provider (its kwargs aren't important for this test)
    fake_get_llm = _make_fake_get_llm(capture)
    monkeypatch.setattr(llm_module, 'get_llm', fake_get_llm)

    prompt_family = _make_prompt_family()

    config = _make_config(smart_llm_model='any-model', llm_kwargs=None)

    original_subtopics = ['keep-me']

    # Run and verify that on exception we receive the original subtopics back
    result = asyncio.run(construct_subtopics('task-ex', 'data-ex', config, subtopics=original_subtopics, prompt_family=prompt_family))

    assert result is original_subtopics or result == original_subtopics
