# file: rdagent/oai/backend/deprec.py:294-465
# asked: {"lines": [310, 311, 314, 315, 316, 317, 318, 320, 321, 322, 323, 324, 325, 326, 327, 329, 330, 331, 332, 333, 334, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 370, 371, 372, 373, 374, 375, 376, 378, 379, 381, 382, 384, 385, 386, 387, 388, 390, 391, 392, 393, 394, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 407, 408, 409, 410, 411, 412, 413, 414, 415, 419, 420, 421, 422, 424, 425, 426, 428, 429, 431, 432, 434, 435, 436, 437, 438, 440, 441, 442, 443, 444, 446, 447, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 463, 465], "branches": [[310, 311], [310, 314], [320, 321], [320, 329], [321, 322], [321, 329], [322, 321], [322, 323], [325, 326], [325, 327], [330, 331], [330, 339], [337, 338], [337, 465], [339, 340], [339, 360], [358, 359], [358, 465], [360, 361], [360, 407], [362, 363], [362, 370], [363, 364], [363, 365], [365, 366], [365, 367], [367, 362], [367, 368], [378, 379], [378, 396], [381, 382], [381, 384], [384, 385], [384, 401], [390, 391], [390, 392], [393, 384], [393, 394], [399, 400], [399, 401], [403, 404], [403, 465], [419, 420], [419, 426], [420, 421], [420, 425], [422, 420], [422, 424], [428, 429], [428, 450], [431, 432], [431, 434], [434, 435], [434, 446], [440, 441], [440, 442], [443, 434], [443, 444], [446, 447], [446, 465], [452, 453], [452, 465]]}
# gained: {"lines": [310, 311, 314, 315, 316, 317, 318, 320, 321, 322, 323, 324, 325, 326, 327, 329, 330, 331, 332, 333, 334, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 370, 371, 372, 373, 374, 375, 376, 378, 379, 381, 382, 384, 385, 386, 387, 390, 391, 392, 393, 394, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 407, 408, 409, 410, 411, 412, 413, 414, 415, 419, 420, 421, 422, 424, 425, 426, 428, 429, 431, 432, 434, 435, 436, 437, 440, 441, 442, 443, 444, 446, 447, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 463, 465], "branches": [[310, 311], [320, 321], [320, 329], [321, 322], [322, 323], [325, 326], [330, 331], [330, 339], [337, 338], [339, 340], [339, 360], [358, 359], [360, 361], [360, 407], [362, 363], [362, 370], [363, 364], [363, 365], [365, 366], [365, 367], [367, 368], [378, 379], [378, 396], [381, 382], [384, 385], [384, 401], [390, 391], [393, 384], [393, 394], [399, 400], [403, 404], [419, 420], [419, 426], [420, 421], [422, 420], [422, 424], [428, 429], [428, 450], [431, 432], [434, 435], [434, 446], [440, 441], [443, 434], [443, 444], [446, 447], [452, 453]]}

import json
import re
import types

import pytest

from rdagent.oai.backend.deprec import DeprecBackend
from rdagent.oai import llm_conf
from rdagent.oai.llm_conf import LLM_SETTINGS
from rdagent.log import rdagent_logger as logger


class DummyGenerator:
    def chat_completion(self, messages, max_gen_len=None, temperature=None):
        return [{"generation": {"content": "generated text"}}]


class DummyHTTPResponse:
    def __init__(self, payload_bytes: bytes):
        self._payload = payload_bytes

    def read(self):
        return self._payload


class DummyDelta:
    def __init__(self, content):
        self.content = content


class DummyChoiceChunk:
    def __init__(self, content=None, finish_reason=None):
        self.delta = DummyDelta(content)
        self.finish_reason = finish_reason


class DummyChunk:
    def __init__(self, choices):
        self.choices = choices


class DummyMessage:
    def __init__(self, content, finish_reason=None):
        self.content = content
        self.finish_reason = finish_reason


class DummyChoiceMessage:
    def __init__(self, message: DummyMessage, finish_reason=None):
        self.message = message
        self.finish_reason = finish_reason


class DummyChatCompletionResponse:
    def __init__(self, content, finish_reason, usage=None):
        self.choices = [DummyChoiceMessage(DummyMessage(content), finish_reason)]
        # usage object with attributes used in logging
        class U:
            pass

        if usage is None:
            u = U()
            u.total_tokens = 1
            u.prompt_tokens = 1
            u.completion_tokens = 1
            self.usage = u
        else:
            self.usage = usage


def _make_deprec_instance():
    # create instance without invoking __init__ that may have heavy side-effects
    inst = object.__new__(DeprecBackend)
    # minimal attributes used in _create_chat_completion_inner_function
    inst._build_log_messages = lambda messages: "LOGGED"
    inst.chat_model_map = {}
    inst.chat_stream = False
    inst.chat_seed = 123
    inst.headers = {}
    inst.gcr_endpoint = "http://example.com/endpoint"
    inst.gcr_endpoint_temperature = 0.1
    inst.gcr_endpoint_top_p = 0.2
    inst.gcr_endpoint_do_sample = False
    inst.gcr_endpoint_max_token = 50
    inst.chat_client = types.SimpleNamespace()
    inst.client = types.SimpleNamespace()
    inst.generator = DummyGenerator()
    inst.chat_use_azure_deepseek = False
    inst.use_gcr_endpoint = False
    inst.use_llama2 = False
    return inst


def test_use_llama2_branch(monkeypatch):
    inst = _make_deprec_instance()
    # Configure LLM settings to log messages and to use llama2 branch
    monkeypatch.setattr(LLM_SETTINGS, "log_llm_chat_content", True)
    inst.use_llama2 = True

    resp, finish = DeprecBackend._create_chat_completion_inner_function(inst, [{"role": "user", "content": "hi"}])
    assert resp == "generated text"
    assert finish is None


def test_use_gcr_endpoint_branch(monkeypatch):
    inst = _make_deprec_instance()
    monkeypatch.setattr(LLM_SETTINGS, "log_llm_chat_content", True)
    inst.use_gcr_endpoint = True
    inst.gcr_endpoint = "http://fake"
    inst.headers = {"Content-Type": "application/json"}

    payload = json.dumps({"output": "gcr-output"}).encode()

    def fake_urlopen(req):
        return DummyHTTPResponse(payload)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    resp, finish = DeprecBackend._create_chat_completion_inner_function(inst, [{"role": "user", "content": "hello"}])
    assert resp == "gcr-output"
    assert finish is None


def test_azure_deepseek_streaming_and_think_extraction(monkeypatch):
    inst = _make_deprec_instance()
    monkeypatch.setattr(LLM_SETTINGS, "log_llm_chat_content", True)
    # simulate azure deepseek streaming branch
    inst.chat_use_azure_deepseek = True
    inst.chat_stream = True

    # create streaming chunks: two chunks with content and a finish_reason in second
    chunk1 = DummyChunk([DummyChoiceChunk(content="<think>thought</think>ans")])
    chunk2 = DummyChunk([DummyChoiceChunk(content="wer", finish_reason="stop")])
    inst.client.complete = lambda **kwargs: [chunk1, chunk2]

    messages = [
        {"role": "system", "content": "system msg"},
        {"role": "user", "content": "user msg"},
        {"role": "assistant", "content": "assistant msg"},
    ]

    resp, finish = DeprecBackend._create_chat_completion_inner_function(inst, messages)
    # the joined streaming response becomes "<think>thought</think>answer"
    assert resp == "answer"
    assert finish == "stop"


def test_azure_deepseek_non_streaming_and_think_logging(monkeypatch):
    inst = _make_deprec_instance()
    monkeypatch.setattr(LLM_SETTINGS, "log_llm_chat_content", True)
    inst.chat_use_azure_deepseek = True
    inst.chat_stream = False

    # create a ChatCompletion-like response
    resp_obj = types.SimpleNamespace()
    resp_obj.choices = [types.SimpleNamespace(message=types.SimpleNamespace(content="<think>X</think>final answer"), finish_reason="done")]
    inst.client.complete = lambda **kwargs: resp_obj

    resp, finish = DeprecBackend._create_chat_completion_inner_function(inst, [{"role": "user", "content": "q"}])
    assert resp == "final answer"
    assert finish == "done"


def test_default_branch_response_format_and_stream_false_and_chat_model_map(monkeypatch):
    inst = _make_deprec_instance()
    monkeypatch.setattr(LLM_SETTINGS, "log_llm_chat_content", True)
    # ensure not using other backends
    inst.use_llama2 = False
    inst.use_gcr_endpoint = False
    inst.chat_use_azure_deepseek = False
    # set chat_model_map and logger tag to exercise model selection branch
    inst.chat_model_map = {"mytag": {"model": "mymodel", "temperature": "0.55", "max_tokens": "77"}}
    monkeypatch.setattr(logger, "_tag", "mytag")

    inst.chat_stream = False

    # prepare messages where first (system) will stop the json injection loop
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "u1"},
    ]

    # fake create to capture call kwargs and return a non-streaming response object
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return DummyChatCompletionResponse(content='{"ok": true}', finish_reason="finished")

    # attach fake chat client structure expected by code
    inst.chat_client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=fake_create)))

    resp, finish = DeprecBackend._create_chat_completion_inner_function(inst, messages, response_format={"type": "json_object"}, add_json_in_prompt=True)
    # ensure it returned the content from response
    assert resp == '{"ok": true}'
    assert finish == "finished"
    # ensure the messages were mutated to include the json prompt on the first encountered system message (loop reversed)
    assert "Please respond in json format." in messages[0]["content"]
    # ensure the call_kwargs includes response_format and model set from chat_model_map
    assert captured.get("response_format") == {"type": "json_object"}
    assert captured.get("model") == "mymodel"
    # temperature overridden as float
    assert abs(float(captured.get("temperature")) - 0.55) < 1e-6
    assert int(captured.get("max_tokens")) == 77


def test_default_branch_streaming_true(monkeypatch):
    inst = _make_deprec_instance()
    monkeypatch.setattr(LLM_SETTINGS, "log_llm_chat_content", True)
    inst.use_llama2 = False
    inst.use_gcr_endpoint = False
    inst.chat_use_azure_deepseek = False
    inst.chat_stream = True

    # create streaming chunks and attach to chat_client.create
    chunk1 = DummyChunk([DummyChoiceChunk(content="he")])
    chunk2 = DummyChunk([DummyChoiceChunk(content="llo", finish_reason="stop")])
    def fake_create(**kwargs):
        return [chunk1, chunk2]

    inst.chat_client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=fake_create)))
    messages = [{"role": "user", "content": "hi"}]
    resp, finish = DeprecBackend._create_chat_completion_inner_function(inst, messages)
    assert resp == "hello"
    assert finish == "stop"
