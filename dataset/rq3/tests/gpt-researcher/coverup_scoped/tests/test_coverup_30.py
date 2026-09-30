# file: gpt_researcher/utils/llm.py:152-213
# asked: {"lines": [174, 175, 177, 178, 179, 180, 181, 184, 186, 187, 189, 190, 192, 193, 195, 197, 199, 201, 202, 203, 204, 205, 206, 208, 210, 211, 212, 213], "branches": [[186, 187], [186, 189], [189, 190], [189, 192]]}
# gained: {"lines": [174, 175, 177, 178, 179, 180, 181, 184, 186, 187, 189, 192, 193, 195, 197, 199, 201, 202, 203, 204, 205, 206, 208, 210, 211, 212, 213], "branches": [[186, 187], [189, 192]]}

import asyncio
import types
import importlib
import pytest


async def _import_llm_module():
    """
    Try both possible module paths to import the llm module used in the code under test.
    Returns the imported module.
    """
    try:
        return importlib.import_module("gpt_researcher.gpt_researcher.utils.llm")
    except ModuleNotFoundError:
        return importlib.import_module("gpt_researcher.utils.llm")


@pytest.mark.asyncio
async def test_construct_subtopics_non_reasoning_model(monkeypatch):
    llm_module = await _import_llm_module()

    called = {}

    # Stub PromptFamily to pass into function
    class StubPromptFamily:
        @staticmethod
        def generate_subtopics_prompt():
            return "stub-template"

    # Stub Parser
    class StubParser:
        def __init__(self, pydantic_object=None):
            # record that constructor was called with expected object
            called["pydantic_object"] = pydantic_object

        def get_format_instructions(self):
            called["format_instructions_called"] = True
            return "FORMAT-INSTR"

    # Chain pieces: PromptTemplate | Model | Parser -> Chain with ainvoke
    class StubPromptTemplate:
        def __init__(self, template, input_variables=None, partial_variables=None):
            # record inputs for assertions
            called["template"] = template
            called["input_variables"] = input_variables
            called["partial_variables"] = partial_variables

        def __or__(self, other):
            # return an intermediate that can be OR'd with parser
            that = self

            class Intermediate:
                def __init__(self, left):
                    self.left = left

                def __or__(self, parser):
                    # return chain object
                    class Chain:
                        async def ainvoke(self, inputs, **kwargs):
                            # verify inputs forwarded properly
                            called["ainvoke_inputs"] = inputs
                            called["ainvoke_kwargs"] = kwargs
                            # produce sample output as parser would
                            return [{"title": "sub1"}, {"title": "sub2"}]

                    return Chain()

            return Intermediate(that)

    # Stub model/provider to be returned by get_llm
    class StubModel:
        pass

    def fake_get_llm(provider_name, **kwargs):
        # record provider name and kwargs used
        called["get_llm_provider_name"] = provider_name
        called["get_llm_kwargs"] = kwargs
        return types.SimpleNamespace(llm=StubModel())

    # Prepare config object: model not in SUPPORT_REASONING_EFFORT_MODELS to test else branch
    class Config:
        smart_llm_model = "non_reasoning_model"
        llm_kwargs = {"custom": "value"}
        temperature = 0.7
        smart_token_limit = 512
        smart_llm_provider = "fake_provider"
        max_subtopics = 5

    config = Config()

    # Monkeypatch module attributes
    monkeypatch.setattr(llm_module, "PydanticOutputParser", StubParser)
    monkeypatch.setattr(llm_module, "PromptTemplate", StubPromptTemplate)
    monkeypatch.setattr(llm_module, "get_llm", fake_get_llm)
    # Ensure SUPPORT_REASONING_EFFORT_MODELS does NOT contain our model
    monkeypatch.setattr(llm_module, "SUPPORT_REASONING_EFFORT_MODELS", set())

    # Import the function under test from the module
    construct_subtopics = getattr(llm_module, "construct_subtopics")

    # Call function
    result = await construct_subtopics(
        task="Test Task",
        data="Some data",
        config=config,
        subtopics=["existing1"],
        prompt_family=StubPromptFamily,
        extra_kw="ignored",
    )

    # Assertions on returned value
    assert isinstance(result, list)
    assert result == [{"title": "sub1"}, {"title": "sub2"}]

    # Ensure the parser constructor was called with a pydantic object (whatever is present in module)
    assert "pydantic_object" in called and called["pydantic_object"] is not None

    assert called.get("format_instructions_called") is True
    assert called.get("template") == "stub-template"
    assert called.get("input_variables") == ["task", "data", "subtopics", "max_subtopics"]
    # partial_variables should include format_instructions
    pv = called.get("partial_variables") or {}
    assert "format_instructions" in pv and pv["format_instructions"] == "FORMAT-INSTR"

    # Ensure get_llm was called with provider name and kwargs that include update from llm_kwargs and temperature/max_tokens
    assert called.get("get_llm_provider_name") == config.smart_llm_provider
    got_kwargs = called.get("get_llm_kwargs")
    assert got_kwargs is not None
    # model key must be present and equal to config.smart_llm_model
    assert got_kwargs.get("model") == config.smart_llm_model
    # custom llm_kwargs merged
    assert got_kwargs.get("custom") == "value"
    # since model not in SUPPORT_REASONING_EFFORT_MODELS, temperature and max_tokens should be present
    assert got_kwargs.get("temperature") == config.temperature
    assert got_kwargs.get("max_tokens") == config.smart_token_limit

    # Ensure chain received inputs and extra kwargs forwarded
    assert called.get("ainvoke_inputs") == {
        "task": "Test Task",
        "data": "Some data",
        "subtopics": ["existing1"],
        "max_subtopics": config.max_subtopics,
    }
    # extra kw forwarded into ainvoke kwargs
    assert called.get("ainvoke_kwargs") == {"extra_kw": "ignored"}


@pytest.mark.asyncio
async def test_construct_subtopics_exception_path_returns_input_subtopics(monkeypatch, capsys):
    llm_module = await _import_llm_module()

    # Make PydanticOutputParser raise on construction to trigger exception path
    class BrokenParser:
        def __init__(self, pydantic_object=None):
            raise RuntimeError("parser failed")

    monkeypatch.setattr(llm_module, "PydanticOutputParser", BrokenParser)

    # Minimal config
    class Config:
        smart_llm_model = "anything"
        llm_kwargs = None
        temperature = 0.5
        smart_token_limit = 100
        smart_llm_provider = "p"
        max_subtopics = 3

    config = Config()

    construct_subtopics = getattr(llm_module, "construct_subtopics")

    initial_subtopics = ["a", "b"]
    result = await construct_subtopics(
        task="T",
        data="D",
        config=config,
        subtopics=initial_subtopics,
    )

    # Should return the original subtopics on exception
    assert result is initial_subtopics or result == initial_subtopics
    # The function prints the exception; ensure something was printed
    captured = capsys.readouterr()
    assert "Exception in parsing subtopics" in (captured.out + captured.err)
