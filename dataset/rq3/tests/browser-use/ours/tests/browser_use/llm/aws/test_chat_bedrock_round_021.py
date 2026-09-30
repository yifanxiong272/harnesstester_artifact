import sys
import types
import json
import pytest
from types import SimpleNamespace

from browser_use.llm.aws.chat_bedrock import (
    ChatAWSBedrock,
    ModelProviderError,
    ModelRateLimitError,
)
from browser_use.llm.aws import chat_bedrock as chat_module

# Helpers to inject a fake botocore.exceptions.ClientError used by ainvoke
class FakeClientError(Exception):
    def __init__(self, response):
        super().__init__(str(response))
        self.response = response


@pytest.fixture(autouse=True)
def ensure_fake_botocore(monkeypatch):
    """Ensure a fake botocore.exceptions module is available so ainvoke's
    runtime import of ClientError succeeds deterministically."""
    fake_mod = types.ModuleType("botocore.exceptions")
    fake_mod.ClientError = FakeClientError
    sys.modules["botocore.exceptions"] = fake_mod
    yield
    # cleanup
    sys.modules.pop("botocore.exceptions", None)


@pytest.mark.asyncio
async def test_text_response_round_021(monkeypatch):
    # Arrange: prepare instance and monkeypatch collaborators
    model = ChatAWSBedrock()

    # Fake serializer returns bedrock_messages and a system message to hit that branch
    monkeypatch.setattr(
        chat_module.AWSBedrockMessageSerializer,
        "serialize_messages",
        staticmethod(lambda messages: ([{"role": "user", "content": "x"}], "SYSTEM_MSG")),
    )

    # Ensure inference config and request_params branches are taken
    monkeypatch.setattr(model, "_get_inference_config", lambda: {"ic": 1})
    model.request_params = {"extra": None, "present": 42}

    # Mock client to capture call and return a text content response
    class DummyClient:
        def __init__(self):
            self.last_call = None

        def converse(self, **kwargs):
            self.last_call = kwargs
            return {
                "output": {
                    "message": {
                        "content": [
                            {"text": "hello"},
                            {"text": "world"},
                            {"other": "ignored"},
                        ]
                    }
                }
            }

    dummy = DummyClient()
    monkeypatch.setattr(model, "_get_client", lambda: dummy)
    monkeypatch.setattr(model, "_get_usage", lambda response: {"tokens": 3})

    # Act
    result = await model.ainvoke(messages=[SimpleNamespace()], output_format=None)

    # Assert: joined text lines and usage forwarded
    assert hasattr(result, "completion")
    assert result.completion == "hello\nworld"
    assert result.usage == {"tokens": 3}
    # Also assert the client received expected keys (modelId and messages present)
    assert dummy.last_call["modelId"] == model.model
    assert "messages" in dummy.last_call
    # system should have been included in kwargs because serializer returned one
    assert dummy.last_call.get("system") == "SYSTEM_MSG"


class DummyOutputModel:
    @classmethod
    def model_validate(cls, data):
        # Returns an identifiable object so tests can assert correct flow
        return {"validated": data}


@pytest.mark.asyncio
async def test_structured_success_round_021(monkeypatch):
    # Arrange: structured output via toolUse with a dict input that validates cleanly
    model = ChatAWSBedrock()

    monkeypatch.setattr(
        chat_module.AWSBedrockMessageSerializer,
        "serialize_messages",
        staticmethod(lambda messages: ([{"role": "user"}], None)),
    )

    # _get_inference_config returns None to exercise that branch
    monkeypatch.setattr(model, "_get_inference_config", lambda: None)

    class ClientWithTool:
        def converse(self, **kwargs):
            return {
                "output": {
                    "message": {
                        "content": [
                            {
                                "toolUse": {
                                    "input": {"field": "value"}
                                }
                            }
                        ]
                    }
                }
            }

    monkeypatch.setattr(model, "_get_client", lambda: ClientWithTool())
    monkeypatch.setattr(model, "_get_usage", lambda response: {"u": True})

    # Act
    result = await model.ainvoke(messages=[SimpleNamespace()], output_format=DummyOutputModel)

    # Assert: completion is the validated structure returned by DummyOutputModel.model_validate
    assert isinstance(result, chat_module.ChatInvokeCompletion)
    assert result.completion == {"validated": {"field": "value"}}
    assert result.usage == {"u": True}


class FlakyModel:
    @classmethod
    def model_validate(cls, data):
        # Fail when passed a plain string, succeed for mappings
        if isinstance(data, str):
            raise Exception("string-input-not-acceptable")
        return {"ok": data}


@pytest.mark.asyncio
async def test_structured_json_parse_round_021(monkeypatch):
    # Arrange: tool input is a JSON string; first model_validate will raise, JSON parsed and validated
    model = ChatAWSBedrock()

    monkeypatch.setattr(
        chat_module.AWSBedrockMessageSerializer,
        "serialize_messages",
        staticmethod(lambda messages: ([{"role": "user"}], None)),
    )

    class ClientWithJSONString:
        def converse(self, **kwargs):
            return {
                "output": {
                    "message": {
                        "content": [
                            {"toolUse": {"input": json.dumps({"a": 1})}}
                        ]
                    }
                }
            }

    monkeypatch.setattr(model, "_get_client", lambda: ClientWithJSONString())
    monkeypatch.setattr(model, "_get_usage", lambda response: {"u": 2})

    # Act
    result = await model.ainvoke(messages=[SimpleNamespace()], output_format=FlakyModel)

    # Assert: JSON string was parsed, validated, and returned
    assert result.completion == {"ok": {"a": 1}}
    assert result.usage == {"u": 2}


@pytest.mark.asyncio
async def test_structured_validation_failure_round_021(monkeypatch):
    # Arrange: model_validate always fails and tool input is non-JSON string -> ModelProviderError
    model = ChatAWSBedrock()

    monkeypatch.setattr(
        chat_module.AWSBedrockMessageSerializer,
        "serialize_messages",
        staticmethod(lambda messages: ([{"role": "user"}], None)),
    )

    class ClientWithBadString:
        def converse(self, **kwargs):
            return {
                "output": {
                    "message": {
                        "content": [
                            {"toolUse": {"input": "not-a-json"}}
                        ]
                    }
                }
            }

    monkeypatch.setattr(model, "_get_client", lambda: ClientWithBadString())

    class AlwaysFailModel:
        @classmethod
        def model_validate(cls, data):
            raise Exception("validation failed always")

    # Act & Assert
    with pytest.raises(ModelProviderError) as exc:
        await model.ainvoke(messages=[SimpleNamespace()], output_format=AlwaysFailModel)

    assert "Failed to validate structured output" in str(exc.value)


@pytest.mark.asyncio
async def test_client_error_rate_limit_and_provider_round_021(monkeypatch):
    # Arrange: simulate ClientError with throttling code and then a generic error
    model = ChatAWSBedrock()

    monkeypatch.setattr(
        chat_module.AWSBedrockMessageSerializer,
        "serialize_messages",
        staticmethod(lambda messages: ([{"role": "user"}], None)),
    )

    class ClientRaisesThrottle:
        def converse(self, **kwargs):
            raise FakeClientError({"Error": {"Code": "ThrottlingException", "Message": "throttle"}})

    monkeypatch.setattr(model, "_get_client", lambda: ClientRaisesThrottle())

    # Throttling should map to ModelRateLimitError
    with pytest.raises(ModelRateLimitError) as excinfo:
        await model.ainvoke(messages=[SimpleNamespace()], output_format=None)
    assert "throttle" in str(excinfo.value)

    # Now test generic provider error mapping
    class ClientRaisesOther:
        def converse(self, **kwargs):
            raise FakeClientError({"Error": {"Code": "SomeOther", "Message": "boom"}})

    monkeypatch.setattr(model, "_get_client", lambda: ClientRaisesOther())

    with pytest.raises(ModelProviderError) as excinfo2:
        await model.ainvoke(messages=[SimpleNamespace()], output_format=None)
    assert "boom" in str(excinfo2.value)
