import pytest
from types import SimpleNamespace
import asyncio

from browser_use.llm.mistral.chat import ChatMistral
from browser_use.llm.mistral import chat as chat_mod
from browser_use.llm.exceptions import ModelProviderError
from browser_use.llm.views import ChatInvokeUsage, ChatInvokeCompletion


@pytest.mark.asyncio
async def test_ainvoke_with_output_format_round_068(monkeypatch):
    """
    Verifies generation params are placed into payload and response_format is built when output_format
    is provided. Also verifies parsed output is returned via output_format.model_validate_json.
    """
    captured = {}

    # Create instance with non-default generation params to exercise payload branches
    cm = ChatMistral(
        temperature=0.5,
        top_p=0.9,
        max_tokens=100,
        seed=42,
        safe_prompt=True,
        api_key="fake-key",
    )

    # Patch _serialize_messages to produce a deterministic messages payload
    monkeypatch.setattr(cm, "_serialize_messages", lambda messages: [{"role": "user", "content": "hi"}])

    # Patch MistralSchemaOptimizer.create_mistral_compatible_schema where chat module resolves it
    monkeypatch.setattr(chat_mod.MistralSchemaOptimizer, "create_mistral_compatible_schema", staticmethod(lambda of: {"m_schema": "ok"}))

    # Patch _extract_content_text to return json text that will be parsed by output_format
    monkeypatch.setattr(cm, "_extract_content_text", lambda choice: '{"parsed": true}')

    # Patch _build_usage to return a concrete ChatInvokeUsage
    monkeypatch.setattr(cm, "_build_usage", lambda u: ChatInvokeUsage(prompt_tokens=1, completion_tokens=2, total_tokens=3))

    # Capture the payload passed into _post and return a normal response with a single choice
    async def fake_post(payload):
        captured['payload'] = payload
        return {"choices": [{"unused": True}], "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}}

    monkeypatch.setattr(cm, "_post", fake_post)

    # Create a minimal output_format with the required model_validate_json call
    class DummyFormat:
        @staticmethod
        def model_validate_json(text: str):
            # Assert we received the content text we set above
            assert text == '{"parsed": true}'
            return {"validated": True}

    # Call ainvoke with an output_format to exercise response_format branch
    result = await cm.ainvoke(messages=[SimpleNamespace()], output_format=DummyFormat)

    # Validate payload included generation params and response_format schema
    payload = captured.get('payload')
    assert payload is not None
    assert payload['temperature'] == 0.5
    assert payload['top_p'] == 0.9
    assert payload['max_tokens'] == 100
    assert payload['seed'] == 42
    assert payload['safe_prompt'] is True

    # Response format should be present and contain the schema returned by the patched optimizer
    rf = payload.get('response_format')
    assert isinstance(rf, dict)
    assert rf.get('type') == 'json_schema'
    assert rf['json_schema']['schema'] == {"m_schema": "ok"}

    # Validate returned ChatInvokeCompletion holds the parsed object and the usage created above
    assert isinstance(result, ChatInvokeCompletion)
    assert result.completion == {"validated": True}
    assert isinstance(result.usage, ChatInvokeUsage)
    assert result.usage.total_tokens == 3


@pytest.mark.asyncio
async def test_ainvoke_no_choices_raises_round_068(monkeypatch):
    """
    When the provider returns no choices, ainvoke should raise ModelProviderError with the
    provider-specific message.
    """
    cm = ChatMistral(api_key="fake-key")

    # Ensure serialized messages don't matter for this test
    monkeypatch.setattr(cm, "_serialize_messages", lambda messages: [])

    async def fake_post_empty(payload):
        return {"choices": []}

    monkeypatch.setattr(cm, "_post", fake_post_empty)

    with pytest.raises(ModelProviderError) as excinfo:
        await cm.ainvoke(messages=[], output_format=None)

    # The implementation raises ModelProviderError('Mistral returned no choices', model=self.name)
    assert "Mistral returned no choices" in str(excinfo.value)


@pytest.mark.asyncio
async def test_ainvoke_post_exception_mapped_round_068(monkeypatch, caplog):
    """
    If _post raises a generic Exception, ainvoke should log an error and raise ModelProviderError
    wrapping the original message.
    """
    cm = ChatMistral(api_key="fake-key")

    monkeypatch.setattr(cm, "_serialize_messages", lambda messages: [])

    async def fake_post_raises(payload):
        raise RuntimeError("upstream failure")

    monkeypatch.setattr(cm, "_post", fake_post_raises)

    with pytest.raises(ModelProviderError) as excinfo:
        await cm.ainvoke(messages=[], output_format=None)

    # The raised ModelProviderError should carry the original message
    assert "upstream failure" in str(excinfo.value)
    # The logger call should have emitted an error mentioning the failure
    assert any("Mistral invocation failed" in rec.message for rec in caplog.records)
