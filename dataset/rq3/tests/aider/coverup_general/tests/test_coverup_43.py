# file: aider/coders/base_coder.py:1127-1172
# asked: {"lines": [1131, 1133, 1150, 1151, 1152, 1156, 1157, 1158, 1159, 1161, 1164, 1165, 1166, 1169, 1170], "branches": [[1149, 1150], [1150, 1151], [1150, 1156], [1157, 1158], [1157, 1163], [1158, 1159], [1158, 1161], [1163, 1164], [1164, 1165], [1164, 1169]]}
# gained: {"lines": [1131, 1133, 1150, 1151, 1152, 1156, 1157, 1158, 1159, 1161, 1164, 1165, 1166, 1169, 1170], "branches": [[1149, 1150], [1150, 1151], [1150, 1156], [1157, 1158], [1157, 1163], [1158, 1159], [1158, 1161], [1163, 1164], [1164, 1165], [1164, 1169]]}

import os
from datetime import datetime

import pytest

from aider.coders import base_coder
from aider.coders.base_coder import Coder


def _current_date_str():
    return datetime.now().astimezone().strftime("%Y-%m-%d")


class DummyIO:
    def __init__(self):
        self.pretty = False
        self.encoding = "utf-8"
        self.chat_history_file = "/dev/null"

    def read_text(self, path):
        return ""

    def tool_output(self, *args, **kwargs):
        # emulate logging, but do nothing
        pass

    def tool_warning(self, *args, **kwargs):
        pass


class DummyCommands:
    def __init__(self, io, coder):
        self.io = io
        self.coder = coder


def make_main_model():
    class MM:
        def __init__(self):
            self.reasoning_tag = None
            self.streaming = True
            self.cache_control = False
            self.info = {}
            self.weak_model = object()
            self.max_chat_history_tokens = 0

        def commit_message_models(self):
            return []

    return MM()


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    # Replace potentially heavy classes with safe dummies
    monkeypatch.setattr(base_coder, "Commands", DummyCommands)
    # Allow Linter to be a no-op constructor that returns None
    monkeypatch.setattr(base_coder, "Linter", lambda *args, **kwargs: None)
    # Ensure GitRepo/RepoMap/ChatSummary not used (use_git=False in tests)
    monkeypatch.setattr(base_coder, "GitRepo", lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError()))
    monkeypatch.setattr(base_coder, "RepoMap", lambda *args, **kwargs: None)
    monkeypatch.setattr(base_coder, "ChatSummary", lambda *args, **kwargs: None)
    yield


def test_get_platform_info_handles_platform_keyerror_and_no_user_language(monkeypatch):
    # Simulate platform.platform() raising KeyError to hit the except branch
    def raise_keyerror():
        raise KeyError("no platform")
    monkeypatch.setattr(base_coder.platform, "platform", raise_keyerror)

    # Ensure both possible shell env vars are set so the function can read whichever is used
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.setenv("COMSPEC", "C:\\Windows\\cmd.exe")

    io = DummyIO()
    main_model = make_main_model()

    # Construct Coder with minimal required args and avoid git usage
    coder = Coder(main_model, io, use_git=False, summarizer=object())

    # No repo, no lint/test commands, and get_user_language returns None
    coder.repo = False
    coder.lint_cmds = None
    coder.test_cmd = None
    monkeypatch.setattr(coder, "get_user_language", lambda: None)

    info = coder.get_platform_info()

    # Assertions to verify the KeyError branch and other expected content
    assert "- Platform information unavailable" in info
    # Determine which shell var was used by inspecting the module's os.name
    shell_var = "COMSPEC" if base_coder.os.name == "nt" else "SHELL"
    expected_shell_line = f"- Shell: {shell_var}="
    assert expected_shell_line in info
    # No language line should be present
    assert "- Language:" not in info
    # No repo line
    assert "- The user is operating inside a git repository" not in info
    # Current date should be present
    assert f"- Current date: {_current_date_str()}" in info


def test_get_platform_info_lint_and_test_variants(monkeypatch):
    # Normal platform info
    monkeypatch.setattr(base_coder.platform, "platform", lambda: "TestOS-1.2.3")

    # Ensure both possible shell env vars are set
    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.setenv("COMSPEC", "C:\\Windows\\cmd.exe")

    io = DummyIO()
    main_model = make_main_model()

    coder = Coder(main_model, io, use_git=False, summarizer=object())

    # Make sure repo is detected to hit that branch
    coder.repo = True
    # Provide a user language to hit that branch
    monkeypatch.setattr(coder, "get_user_language", lambda: "en-US")

    # Provide lint commands including a None key and a language key
    coder.lint_cmds = {None: "flake8", "python": "pytest -q"}
    coder.test_cmd = "pytest -q"

    # First variant: auto_lint True, auto_test True
    coder.auto_lint = True
    coder.auto_test = True

    info_precommit = coder.get_platform_info()

    # Should include the pre-commit lint header
    assert "pre-commit runs these lint commands" in info_precommit
    # Should list the lint commands, including the None-key entry and the language-specific entry
    assert "  - flake8" in info_precommit
    assert "  - python: pytest -q" in info_precommit

    # Should include the pre-commit test header and the test command
    assert "pre-commit runs this test command" in info_precommit
    assert "pytest -q" in info_precommit

    # Repo and language and shell and date should be present
    assert "- The user is operating inside a git repository" in info_precommit
    assert "- Language: en-US" in info_precommit
    shell_var = "COMSPEC" if base_coder.os.name == "nt" else "SHELL"
    assert f"- Shell: {shell_var}=" in info_precommit
    assert f"- Current date: {_current_date_str()}" in info_precommit

    # Second variant: auto_lint False, auto_test False
    coder.auto_lint = False
    coder.auto_test = False

    info_user_pref = coder.get_platform_info()

    # Should include the user-preferred lint header
    assert "The user prefers these lint commands" in info_user_pref
    # Lint command entries should still be present and formatted the same
    assert "  - flake8" in info_user_pref
    assert "  - python: pytest -q" in info_user_pref

    # Should include the user-preferred test header and the test command followed by newline
    assert "The user prefers this test command" in info_user_pref
    assert "pytest -q" in info_user_pref

    # Repo and language and shell and date should still be present
    assert "- The user is operating inside a git repository" in info_user_pref
    assert "- Language: en-US" in info_user_pref
    assert f"- Shell: {shell_var}=" in info_user_pref
    assert f"- Current date: {_current_date_str()}" in info_user_pref
