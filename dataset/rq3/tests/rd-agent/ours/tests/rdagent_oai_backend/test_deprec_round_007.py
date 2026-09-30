import json
import re
from types import SimpleNamespace
import pytest

import rdagent.oai.backend.deprec as deprec


class _CaptureLogger:
    def __init__(self):
        self.records = []
        # allow membership checks like "if t in logger._tag"
        self._tag = []

    def info(self, *args, **kwargs):
        # record invocation for assertions
        self.records.append((args, kwargs))


class DummyChoiceDelta:
    def __init__(self, content):
        self.content = content


class DummyChoice:
    def __init__(self, delta_content=None, finish_reason=None, message_content=None):
        # streaming path uses .delta.content and .finish_reason
        self.delta = DummyChoiceDelta(delta_content)
        self.finish_reason = finish_reason
        # non-streaming path uses .message.content
        self.message = SimpleNamespace(content=message_content)


class DummyChunk:
    def __init__(self, delta_content=None, finish_reason=None):
        self.choices = [DummyChoice(delta_content=delta_content, finish_reason=finish_reason)]


class DummyNonStreamResponse:
    def __init__(self, msg_content, finish_reason, usage=None):
        # mimic the shape used in code: response.choices[0].message.content
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=msg_content), finish_reason=finish_reason)]
        # response.usage
        self.usage = usage or SimpleNamespace(total_tokens=1, prompt_tokens=1, completion_tokens=0)


@pytest.fixture(autouse=True)
def ensure_names(monkeypatch):
    # Provide minimal LLM_SETTINGS structure and a capture logger to avoid external systems
    monkeypatch.setattr(deprec, "LLM_SETTINGS", SimpleNamespace(
        log_llm_chat_content=False,
        chat_model="gpt",
        chat_temperature=0.5,
        chat_max_tokens=64,
        chat_frequency_penalty=0.0,
        chat_presence_penalty=0.0,
        system_prompt_role="system",
    ))

    # Replace module logger with a capture logger
    cap = _CaptureLogger()
    monkeypatch.setattr(deprec, "logger", cap)

    # Provide simple LogColors to avoid attribute errors in f-strings
    monkeypatch.setattr(deprec, "LogColors", SimpleNamespace(CYAN="", END=""))

    # Patch any Azure message classes that may be referenced in the code
    monkeypatch.setattr(deprec, "SystemMessage", lambda content=None: SimpleNamespace(content=content))
    monkeypatch.setattr(deprec, "UserMessage", lambda content=None: SimpleNamespace(content=content))
    monkeypatch.setattr(deprec, "AssistantMessage", lambda content=None: SimpleNamespace(content=content))

    return cap


def test_llama2_branch_logs_and_respects_chat_model_map_round_007(ensure_names, monkeypatch):
    logger = deprec.logger
    # Enable log flow
    deprec.LLM_SETTINGS.log_llm_chat_content = True

    # Ensure logger tags such that chat_model_map's key matches
    logger._tag = ["mytag"]

    # Prepare a self-like object with a generator
    def fake_chat_completion(messages, max_gen_len=None, temperature=None):
        # shape expected by code: a list where element 0 is a dict with key "generation"
        return [{"generation": {"content": "LLAMA_OK"}}]

    self = SimpleNamespace(
        _build_log_messages=lambda m: "LOGGED_MESSAGES",
        chat_model_map={"mytag": {"model": "mymodel", "temperature": "0.1", "max_tokens": "5"}},
        use_llama2=True,
        generator=SimpleNamespace(chat_completion=fake_chat_completion),
        use_gcr_endpoint=False,
        chat_use_azure_deepseek=False,
        chat_stream=False,
        chat_client=None,
        chat_seed=None,
    )

    resp, finish_reason = deprec.DeprecBackend._create_chat_completion_inner_function(
        self, messages=[{"role": "user", "content": "hello"}], response_format=None, add_json_in_prompt=False
    )

    assert resp == "LLAMA_OK"
    assert finish_reason is None

    # verify that logger.info was called at least for messages and response
    assert any("LOGGED_MESSAGES" in str(a) or "LLAMA_OK" in str(a) for a, _ in logger.records)


def test_gcr_endpoint_reads_and_parses_output_round_007(ensure_names, monkeypatch):
    logger = deprec.logger
    deprec.LLM_SETTINGS.log_llm_chat_content = True

    # Create a self-like object configured for GCR endpoint
    self = SimpleNamespace(
        _build_log_messages=lambda m: "LOGGED_MESSAGES",
        use_llama2=False,
        use_gcr_endpoint=True,
        gcr_endpoint="http://fake-gcr",
        gcr_endpoint_temperature=0.1,
        gcr_endpoint_top_p=0.5,
        gcr_endpoint_max_token=20,
        headers={"h": "v"},
        chat_model_map={},
        chat_use_azure_deepseek=False,
        chat_stream=False,
    )

    # Patch urllib to avoid network access
    class DummyResponse:
        def read(self):
            return b'{"output": "GCR_RESPONSE_VALUE"}'

    monkeypatch.setattr(deprec.urllib.request, "Request", lambda *a, **k: (a, k))
    called = {}

    def fake_urlopen(req):
        called['req'] = req
        return DummyResponse()

    monkeypatch.setattr(deprec.urllib.request, "urlopen", fake_urlopen)

    resp, finish_reason = deprec.DeprecBackend._create_chat_completion_inner_function(
        self, messages=[{"role": "user", "content": "ask"}], response_format=None, add_json_in_prompt=False
    )

    assert resp == "GCR_RESPONSE_VALUE"
    assert finish_reason is None
    # ensure our fake urlopen was used
    assert 'req' in called


def test_azure_streaming_aggregates_and_extracts_think_round_007(ensure_names, monkeypatch):
    logger = deprec.logger
    deprec.LLM_SETTINGS.log_llm_chat_content = True

    # prepare streaming chunks that include a <think>...</think> part in the second chunk
    chunk1 = DummyChunk(delta_content="part1", finish_reason=None)
    chunk2 = DummyChunk(delta_content="<think>THOUGHTS</think>final", finish_reason="stop")

    def fake_complete(messages, **kwargs):
        # return an iterable of chunks
        return iter([chunk1, chunk2])

    self = SimpleNamespace(
        _build_log_messages=lambda m: "LOGGED_MESSAGES",
        use_llama2=False,
        use_gcr_endpoint=False,
        chat_use_azure_deepseek=True,
        client=SimpleNamespace(complete=fake_complete),
        chat_stream=True,
        chat_model_map={},
        chat_seed=None,
    )

    resp, finish_reason = deprec.DeprecBackend._create_chat_completion_inner_function(
        self, messages=[{"role": "system", "content": "s"}, {"role": "user", "content": "u"}], response_format=None, add_json_in_prompt=False
    )

    # after processing, the code extracts the think part and returns only the remaining response
    assert resp == "final"
    assert finish_reason == "stop"


def test_response_format_json_inserts_prompt_and_logs_usage_round_007(ensure_names, monkeypatch):
    logger = deprec.logger
    deprec.LLM_SETTINGS.log_llm_chat_content = True
    deprec.LLM_SETTINGS.system_prompt_role = "system"

    # messages include a system role so the loop that appends the JSON instruction will break
    messages = [{"role": "system", "content": "SYS"}, {"role": "user", "content": "USER"}]

    # prepare a non-streaming response object for the default chat client path
    usage = SimpleNamespace(total_tokens=10, prompt_tokens=6, completion_tokens=4)
    fake_response = DummyNonStreamResponse(msg_content='{"ok": true}', finish_reason='completed', usage=usage)

    # chat_client.chat.completions.create should return our fake_response; also support iteration when chat_stream True
    class FakeCompletionsClient:
        def __init__(self, resp):
            self._resp = resp

        def create(self, **kwargs):
            # return the object used by the code
            return self._resp

    chat_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletionsClient(fake_response)))

    self = SimpleNamespace(
        _build_log_messages=lambda m: "LOGGED_MESSAGES",
        use_llama2=False,
        use_gcr_endpoint=False,
        chat_use_azure_deepseek=False,
        chat_client=chat_client,
        chat_stream=False,
        chat_seed=123,
        chat_model_map={},
    )

    # Call with response_format requesting json_object and instruct to add json in prompt
    resp, finish_reason = deprec.DeprecBackend._create_chat_completion_inner_function(
        self, messages=messages, response_format={"type": "json_object"}, add_json_in_prompt=True
    )

    # Response should be passed through from our fake response
    assert resp == '{"ok": true}'
    assert finish_reason == 'completed'

    # the code mutates messages in-place to append the JSON instruction to each message up to system
    assert any(msg["content"].endswith("Please respond in json format.") for msg in messages)

    # verify that logger recorded the usage JSON (string) somewhere
    assert any(isinstance(a[0][0], str) and ('total_tokens' in a[0][0] or 'completion_tokens' in a[0][0]) for a, _ in logger.records)
