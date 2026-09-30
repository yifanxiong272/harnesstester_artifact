# file: aider/coders/chat_chunks.py:28-41
# asked: {"lines": [29, 30, 32, 34, 36, 39, 41], "branches": [[29, 30], [29, 32], [34, 36], [34, 39]]}
# gained: {"lines": [29, 30, 32, 34, 36, 39, 41], "branches": [[29, 30], [29, 32], [34, 36], [34, 39]]}

import pytest
from aider.coders.chat_chunks import ChatChunks

def test_add_cache_control_headers_with_examples_and_repo(monkeypatch):
    # Prepare instance with examples, repo, readonly_files, and chat_files
    cc = ChatChunks(
        system=["system-message"],
        examples=["example-1", "example-2"],
        repo=["repo-meta"],
        readonly_files=["readonly-1"],
        chat_files=["chat-1", "chat-2"],
    )

    calls = []

    # Monkeypatch the instance method to capture calls
    def fake_add_cache_control(messages):
        # record a shallow copy to avoid mutation side-effects
        calls.append(list(messages))

    monkeypatch.setattr(cc, "add_cache_control", fake_add_cache_control, raising=True)

    # Execute the method under test
    cc.add_cache_control_headers()

    # With examples present, first call should be with examples
    # With repo present, second call should be with repo
    # Finally, chat_files should always be called
    assert calls[0] == ["example-1", "example-2"]
    assert calls[1] == ["repo-meta"]
    assert calls[2] == ["chat-1", "chat-2"]
    assert len(calls) == 3

def test_add_cache_control_headers_without_examples_or_repo(monkeypatch):
    # Prepare instance with no examples and no repo, but with system, readonly_files, and chat_files
    cc = ChatChunks(
        system=["only-system"],
        examples=[],
        repo=[],
        readonly_files=["readonly-1", "readonly-2"],
        chat_files=["chat-x"],
    )

    calls = []

    def fake_add_cache_control(messages):
        calls.append(list(messages))

    monkeypatch.setattr(cc, "add_cache_control", fake_add_cache_control, raising=True)

    # Execute the method under test
    cc.add_cache_control_headers()

    # With no examples, should call system first
    assert calls[0] == ["only-system"]
    # With no repo, should call readonly_files next
    assert calls[1] == ["readonly-1", "readonly-2"]
    # chat_files should always be called last
    assert calls[2] == ["chat-x"]
    assert len(calls) == 3
