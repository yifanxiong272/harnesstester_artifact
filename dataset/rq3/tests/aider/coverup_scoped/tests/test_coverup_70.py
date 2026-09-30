# file: aider/coders/chat_chunks.py:28-41
# asked: {"lines": [29, 30, 32, 34, 36, 39, 41], "branches": [[29, 30], [29, 32], [34, 36], [34, 39]]}
# gained: {"lines": [29, 30, 32, 34, 36, 39, 41], "branches": [[29, 30], [29, 32], [34, 36], [34, 39]]}

import pytest
from types import MethodType

from aider.coders.chat_chunks import ChatChunks


def test_add_cache_control_headers_with_examples_and_repo(monkeypatch):
    c = ChatChunks()
    # prepare lists
    c.examples = ["example1"]
    c.repo = ["repo1"]
    c.chat_files = ["chat1"]

    calls = []

    def fake_add_cache_control(self, messages):
        # record the exact object passed to ensure identity
        calls.append(messages)

    # Patch the method on the class so instance method binding works correctly
    monkeypatch.setattr(ChatChunks, "add_cache_control", fake_add_cache_control)

    # Call the method under test
    c.add_cache_control_headers()

    # Expect add_cache_control called first with examples, then with repo, then with chat_files
    assert calls == [c.examples, c.repo, c.chat_files]
    # Make sure each list is the same object that was set on the instance
    assert calls[0] is c.examples
    assert calls[1] is c.repo
    assert calls[2] is c.chat_files


def test_add_cache_control_headers_without_examples_and_without_repo(monkeypatch):
    c = ChatChunks()
    # examples empty -> should use system
    c.examples = []
    c.system = ["system1"]
    # repo empty -> should use readonly_files (even if empty, code calls it)
    c.repo = []
    c.readonly_files = ["readonly1"]
    c.chat_files = ["chat2"]

    calls = []

    def fake_add_cache_control(self, messages):
        calls.append(messages)

    monkeypatch.setattr(ChatChunks, "add_cache_control", fake_add_cache_control)

    c.add_cache_control_headers()

    # Expect add_cache_control called with system, then readonly_files, then chat_files
    assert calls == [c.system, c.readonly_files, c.chat_files]
    assert calls[0] is c.system
    assert calls[1] is c.readonly_files
    assert calls[2] is c.chat_files
