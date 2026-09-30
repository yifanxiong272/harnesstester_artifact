# file: sweagent/agent/models.py:161-179
# asked: {"lines": [168, 170], "branches": [[167, 168], [169, 170], [172, 174]]}
# gained: {"lines": [168, 170], "branches": [[167, 168], [169, 170]]}

import importlib
from types import SimpleNamespace

import pytest


def test_choose_api_key_no_keys(monkeypatch):
    models = importlib.import_module("sweagent.agent.models")
    GenericAPIModelConfig = models.GenericAPIModelConfig

    # create instance (name is required)
    cfg = GenericAPIModelConfig(name="m")

    # Monkeypatch the class method get_api_keys to return empty list to hit the "return None" branch
    monkeypatch.setattr(
        GenericAPIModelConfig,
        "get_api_keys",
        lambda self: [],
        raising=True,
    )

    result = cfg.choose_api_key()
    assert result is None


def test_choose_api_key_random_choice_when_not_by_thread(monkeypatch):
    models = importlib.import_module("sweagent.agent.models")
    GenericAPIModelConfig = models.GenericAPIModelConfig

    cfg = GenericAPIModelConfig(name="m2")
    cfg.choose_api_key_by_thread = False

    # Provide multiple keys and force the module's random.choice to pick the last one deterministically
    monkeypatch.setattr(
        GenericAPIModelConfig,
        "get_api_keys",
        lambda self: ["k1", "k2", "k3"],
        raising=True,
    )
    monkeypatch.setattr(models.random, "choice", lambda seq: seq[-1], raising=True)

    result = cfg.choose_api_key()
    assert result == "k3"


def test_choose_api_key_thread_appends_and_indexes(monkeypatch):
    models = importlib.import_module("sweagent.agent.models")
    GenericAPIModelConfig = models.GenericAPIModelConfig

    # Ensure the module-level tracking list is reset for the test
    monkeypatch.setattr(models, "_THREADS_THAT_USED_API_KEYS", [], raising=False)

    cfg = GenericAPIModelConfig(name="m3")
    cfg.choose_api_key_by_thread = True

    # Provide two API keys so index math is exercised
    monkeypatch.setattr(
        GenericAPIModelConfig,
        "get_api_keys",
        lambda self: ["tk1", "tk2"],
        raising=True,
    )

    # Make current_thread have a deterministic name that is not in the list
    monkeypatch.setattr(models.threading, "current_thread", lambda: SimpleNamespace(name="test-thread-unique"), raising=True)

    result = cfg.choose_api_key()

    # It should have appended the thread name and returned the key at index 0 (thread_idx 0 -> key_idx 0)
    assert result == "tk1"
    assert "test-thread-unique" in models._THREADS_THAT_USED_API_KEYS
    # The thread should be the first and its index should be 0
    assert models._THREADS_THAT_USED_API_KEYS.index("test-thread-unique") == 0
