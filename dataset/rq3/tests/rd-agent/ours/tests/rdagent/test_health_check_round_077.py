import importlib
import os
import types

import pytest

import rdagent.app.utils.health_check as hc


class DummyLogger:
    def __init__(self):
        self.warnings = []
        self.infos = []
        self.errors = []

    def warning(self, msg):
        self.warnings.append(msg)

    def info(self, msg):
        self.infos.append(msg)

    def error(self, msg):
        self.errors.append(msg)


def _clear_env(keys):
    for k in keys:
        os.environ.pop(k, None)


def test_deepseek_with_deepseek_base_round_077(monkeypatch):
    """
    Case: DEEPSEEK_API_KEY and DEEPSEEK_API_BASE are present.
    - Expectation: chat_api_base should be read from DEEPSEEK_API_BASE.
    - test_chat and test_embedding are patched to return True -> final info logged.
    - BACKEND is absent -> a warning is emitted.
    """
    # Ensure clean slate
    keys = [
        "BACKEND",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_API_BASE",
        "OPENAI_API_BASE",
        "OPENAI_API_KEY",
        "LITELLM_PROXY_API_KEY",
        "LITELLM_PROXY_API_BASE",
        "CHAT_MODEL",
        "EMBEDDING_MODEL",
    ]
    _clear_env(keys)

    # Set env for this scenario
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deep_key")
    monkeypatch.setenv("DEEPSEEK_API_BASE", "https://deep.example/api")
    monkeypatch.setenv("LITELLM_PROXY_API_KEY", "proxy_key")
    monkeypatch.setenv("LITELLM_PROXY_API_BASE", "https://proxy.example/api")
    monkeypatch.setenv("CHAT_MODEL", "chat-deep-model")
    monkeypatch.setenv("EMBEDDING_MODEL", "embed-deep-model")

    # Patch logger on module
    dl = DummyLogger()
    monkeypatch.setattr(hc, "logger", dl)

    # Capture calls to test_embedding and test_chat and assert incoming args
    embed_calls = []
    chat_calls = []

    def fake_test_embedding(embedding_model, embedding_api_key, embedding_api_base):
        embed_calls.append((embedding_model, embedding_api_key, embedding_api_base))
        return True

    def fake_test_chat(chat_model, chat_api_key, chat_api_base):
        chat_calls.append((chat_model, chat_api_key, chat_api_base))
        return True

    monkeypatch.setattr(hc, "test_embedding", fake_test_embedding)
    monkeypatch.setattr(hc, "test_chat", fake_test_chat)

    # Run
    hc.env_check()

    # Assertions: warning for BACKEND missing
    assert any("BACKEND" in w for w in dl.warnings), "Expected a warning about BACKEND missing"

    # test_embedding received proxy values
    assert embed_calls, "test_embedding was not called"
    em_model, em_key, em_base = embed_calls[0]
    assert em_model == "embed-deep-model"
    assert em_key == "proxy_key"
    assert em_base == "https://proxy.example/api"

    # test_chat received deepseek base
    assert chat_calls, "test_chat was not called"
    ch_model, ch_key, ch_base = chat_calls[0]
    assert ch_model == "chat-deep-model"
    assert ch_key == "deep_key"
    assert ch_base == "https://deep.example/api"

    # Both returned True -> success info logged
    assert any("All tests completed" in i for i in dl.infos), "Expected success info log"


def test_deepseek_with_openai_base_round_077(monkeypatch):
    """
    Case: DEEPSEEK_API_KEY present, DEEPSEEK_API_BASE missing, OPENAI_API_BASE present.
    - Expectation: chat_api_base should be read from OPENAI_API_BASE (elif branch).
    - Both test functions return True -> success info logged.
    """
    keys = [
        "BACKEND",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_API_BASE",
        "OPENAI_API_BASE",
        "OPENAI_API_KEY",
        "LITELLM_PROXY_API_KEY",
        "LITELLM_PROXY_API_BASE",
        "CHAT_MODEL",
        "EMBEDDING_MODEL",
    ]
    _clear_env(keys)

    monkeypatch.setenv("DEEPSEEK_API_KEY", "deep2_key")
    # intentionally do NOT set DEEPSEEK_API_BASE
    monkeypatch.setenv("OPENAI_API_BASE", "https://openai.example/api")
    monkeypatch.setenv("LITELLM_PROXY_API_KEY", "proxy2_key")
    monkeypatch.setenv("LITELLM_PROXY_API_BASE", "https://proxy2.example/api")
    monkeypatch.setenv("CHAT_MODEL", "chat-deep2-model")
    monkeypatch.setenv("EMBEDDING_MODEL", "embed-deep2-model")

    dl = DummyLogger()
    monkeypatch.setattr(hc, "logger", dl)

    embed_calls = []
    chat_calls = []

    def fake_test_embedding(embedding_model, embedding_api_key, embedding_api_base):
        embed_calls.append((embedding_model, embedding_api_key, embedding_api_base))
        return True

    def fake_test_chat(chat_model, chat_api_key, chat_api_base):
        chat_calls.append((chat_model, chat_api_key, chat_api_base))
        return True

    monkeypatch.setattr(hc, "test_embedding", fake_test_embedding)
    monkeypatch.setattr(hc, "test_chat", fake_test_chat)

    hc.env_check()

    # check chat_api_base used OPENAI_API_BASE
    assert chat_calls, "test_chat not called"
    _, _, chat_base = chat_calls[0]
    assert chat_base == "https://openai.example/api"

    # ensure embedding used proxy values
    assert embed_calls
    _, em_key, em_base = embed_calls[0]
    assert em_key == "proxy2_key"
    assert em_base == "https://proxy2.example/api"

    assert any("All tests completed" in i for i in dl.infos)


def test_openai_key_failure_round_077(monkeypatch):
    """
    Case: OPENAI_API_KEY path used (no DEEPSEEK_API_KEY).
    - Expectation: embedding_api_key and embedding_api_base mirror chat values.
    - test_chat returns False while test_embedding returns True -> final error logged.
    """
    keys = [
        "BACKEND",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_API_BASE",
        "OPENAI_API_BASE",
        "OPENAI_API_KEY",
        "LITELLM_PROXY_API_KEY",
        "LITELLM_PROXY_API_BASE",
        "CHAT_MODEL",
        "EMBEDDING_MODEL",
    ]
    _clear_env(keys)

    # Set OPENAI path
    monkeypatch.setenv("OPENAI_API_KEY", "openai_key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://openai.example/base")
    monkeypatch.setenv("CHAT_MODEL", "chat-openai-model")
    monkeypatch.setenv("EMBEDDING_MODEL", "embed-openai-model")

    dl = DummyLogger()
    monkeypatch.setattr(hc, "logger", dl)

    embed_calls = []
    chat_calls = []

    def fake_test_embedding(embedding_model, embedding_api_key, embedding_api_base):
        embed_calls.append((embedding_model, embedding_api_key, embedding_api_base))
        return True

    def fake_test_chat(chat_model, chat_api_key, chat_api_base):
        chat_calls.append((chat_model, chat_api_key, chat_api_base))
        return False

    monkeypatch.setattr(hc, "test_embedding", fake_test_embedding)
    monkeypatch.setattr(hc, "test_chat", fake_test_chat)

    hc.env_check()

    # embedding_api_key should equal chat_api_key (OPENAI_API_KEY)
    assert embed_calls
    _, em_key, em_base = embed_calls[0]
    assert em_key == "openai_key"
    assert em_base == "https://openai.example/base"

    # chat call observed
    assert chat_calls
    _, ch_key, ch_base = chat_calls[0]
    assert ch_key == "openai_key"
    assert ch_base == "https://openai.example/base"

    # Because test_chat returned False and embedding True -> final error logged
    assert any("One or more tests failed" in e or "One or more tests failed." in e for e in dl.errors), (
        f"Expected failure error log, got infos={dl.infos} warnings={dl.warnings} errors={dl.errors}"
    )
