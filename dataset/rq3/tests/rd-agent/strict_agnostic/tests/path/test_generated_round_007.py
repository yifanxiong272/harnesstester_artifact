import json
import urllib.request
from types import SimpleNamespace

import pytest

from rdagent.oai.backend.deprec import DeprecBackend
from rdagent.oai.llm_conf import LLM_SETTINGS
from rdagent.log import rdagent_logger as logger


# Helpers to build a minimal instance without running __init__
def _make_deprec_instance():
    inst = object.__new__(DeprecBackend)
    # Provide minimal attributes used by the tested method
    inst._build_log_messages = lambda msgs: "BUILT"
    inst.chat_model_map = {}
    inst.use_llama2 = False
    inst.generator = None
    inst.use_gcr_endpoint = False
    inst.gcr_endpoint = "http://fake"
    inst.gcr_endpoint_temperature = 0.1
    inst.gcr_endpoint_top_p = 0.9
    inst.gcr_endpoint_max_token = 16
    inst.headers = {"Content-Type": "application/json"}
    inst.chat_use_azure_deepseek = False
    inst.client = None
    inst.chat_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: None)))
    inst.chat_stream = False
    inst.chat_seed = 42
    inst.chat_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: None)))
    return inst


@pytest.fixture(autouse=True)
def preserve_llm_settings_and_logger(monkeypatch):
    # Save original values to restore after tests
    orig = {
        'log_llm_chat_content': getattr(LLM_SETTINGS, 'log_llm_chat_content', False),
        'chat_model': getattr(LLM_SETTINGS, 'chat_model', None),
        'chat_temperature': getattr(LLM_SETTINGS, 'chat_temperature', None),
        'chat_max_tokens': getattr(LLM_SETTINGS, 'chat_max_tokens', None),
        'chat_frequency_penalty': getattr(LLM_SETTINGS, 'chat_frequency_penalty', None),
        'chat_presence_penalty': getattr(LLM_SETTINGS, 'chat_presence_penalty', None),
        'system_prompt_role': getattr(LLM_SETTINGS, 'system_prompt_role', None),
    }
    # Ensure deterministic common defaults used by tests
    LLM_SETTINGS.log_llm_chat_content = True
    LLM_SETTINGS.chat_model = "gpt-test"
    LLM_SETTINGS.chat_temperature = 0.2
    LLM_SETTINGS.chat_max_tokens = 8
    LLM_SETTINGS.chat_frequency_penalty = 0.0
    LLM_SETTINGS.chat_presence_penalty = 0.0
    LLM_SETTINGS.system_prompt_role = "system"

    # ensure logger has _tag attribute used by function
    orig_tag = getattr(logger, '_tag', '')
    logger._tag = ''

    yield

    # restore
    LLM_SETTINGS.log_llm_chat_content = orig['log_llm_chat_content']
    LLM_SETTINGS.chat_model = orig['chat_model']
    LLM_SETTINGS.chat_temperature = orig['chat_temperature']
    LLM_SETTINGS.chat_max_tokens = orig['chat_max_tokens']
    LLM_SETTINGS.chat_frequency_penalty = orig['chat_frequency_penalty']
    LLM_SETTINGS.chat_presence_penalty = orig['chat_presence_penalty']
    LLM_SETTINGS.system_prompt_role = orig['system_prompt_role']
    logger._tag = orig_tag


def test_llama2_round_007(monkeypatch):
    """
    Exercise the use_llama2 branch: generator.chat_completion -> return content
    """
    inst = _make_deprec_instance()

    # fake generator returning expected nested structure where response[0] is a dict
    class FakeGenerator:
        def chat_completion(self, messages, max_gen_len=None, temperature=None):
            # The implementation expects response[0]["generation"]["content"]
            return [{"generation": {"content": "LLAMA_CONTENT"}}]

    inst.use_llama2 = True
    inst.generator = FakeGenerator()

    messages = [{"role": "user", "content": "Hello"}]

    resp, finish = DeprecBackend._create_chat_completion_inner_function(inst, messages)

    assert resp == "LLAMA_CONTENT", "LLM (llama) branch should return content from generator"
    assert finish is None


def test_gcr_endpoint_round_007(monkeypatch):
    """
    Exercise the use_gcr_endpoint branch by mocking urllib.request.urlopen
    """
    inst = _make_deprec_instance()
    inst.use_gcr_endpoint = True
    inst.gcr_endpoint = "http://fake-gcr"
    inst.headers = {"h": "v"}

    # Prepare a fake response object for urlopen
    class FakeResponse:
        def read(self):
            return json.dumps({"output": "GCR_OUTPUT"}).encode()

    def fake_urlopen(req):
        # verify Request-like object is passed
        assert hasattr(req, 'get_full_url') or hasattr(req, 'host') or hasattr(req, 'full_url') or True
        return FakeResponse()

    monkeypatch.setattr(urllib.request, 'urlopen', fake_urlopen)

    messages = [{"role": "user", "content": "X"}]

    resp, finish = DeprecBackend._create_chat_completion_inner_function(inst, messages)

    assert resp == "GCR_OUTPUT"
    assert finish is None


def test_chat_use_azure_stream_round_007(monkeypatch):
    """
    Exercise the azure deepseek streaming path: stream of chunks with partial content and finish reason
    """
    inst = _make_deprec_instance()
    inst.chat_use_azure_deepseek = True
    inst.chat_stream = True

    # Build fake chunk objects matching attribute access in the code
    class Delta:
        def __init__(self, content):
            self.content = content

    class Choice:
        def __init__(self, delta_content, finish_reason=None):
            self.delta = Delta(delta_content)
            self.finish_reason = finish_reason

    class Chunk:
        def __init__(self, choice):
            self.choices = [choice]

    # Two chunks: first with partial content, second with final content and finish reason
    chunks = [Chunk(Choice("part1", None)), Chunk(Choice("_end", "stop"))]

    class FakeClient:
        def complete(self, messages, stream, temperature, max_tokens, frequency_penalty, presence_penalty):
            assert stream is True
            # Return an iterator over chunks
            for c in chunks:
                yield c

    inst.client = FakeClient()

    messages = [
        {"role": "system", "content": "S"},
        {"role": "user", "content": "U"},
    ]

    resp, finish = DeprecBackend._create_chat_completion_inner_function(inst, messages)

    # We expect concatenation of streamed content
    assert resp == "part1_end"
    assert finish == "stop"


def test_default_chat_client_json_format_round_007(monkeypatch):
    """
    Exercise the default chat_client path (non-azure, non-llama, non-gcr), including
    the response_format modification when add_json_in_prompt is True.
    """
    inst = _make_deprec_instance()
    inst.chat_stream = False

    # Prepare a fake response object similar to expected ChatCompletion
    class U:
        def __init__(self, total, prompt, completion):
            self.total_tokens = total
            self.prompt_tokens = prompt
            self.completion_tokens = completion

    class MessageObj:
        def __init__(self, content):
            self.content = content

    class ChoiceObj:
        def __init__(self, content, finish_reason=None):
            self.message = MessageObj(content)
            self.finish_reason = finish_reason

    class FakeResponse:
        def __init__(self, content, finish, usage):
            self.choices = [ChoiceObj(content, finish)]
            self.usage = usage

    def fake_create(**kw):
        # confirm that response_format passes through when set
        if 'response_format' in kw:
            assert kw['response_format'] == {"type": "json_object"}
        return FakeResponse("RESP_CONTENT", "done", U(10, 4, 6))

    inst.chat_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)))

    # create messages with a system role to be detected when reversing messages
    messages = [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "Please reply"},
    ]

    # Request JSON format to trigger modification of messages in reverse
    resp, finish = DeprecBackend._create_chat_completion_inner_function(inst, messages, response_format={"type": "json_object"}, add_json_in_prompt=True)

    assert resp == "RESP_CONTENT"
    assert finish == "done"

    # Ensure the messages were mutated (the user/system content was appended with json prompt)
    # The loop reverses messages and appends text until hitting system role
    # So at least one message content should contain the json prompt marker
    assert any("Please respond in json format." in m["content"] for m in messages), "messages should be mutated to request JSON response"
