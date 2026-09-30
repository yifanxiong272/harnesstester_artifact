# file: aider/coders/base_coder.py:1127-1172
# asked: {"lines": [1131, 1133, 1150, 1151, 1152, 1156, 1157, 1158, 1159, 1161, 1164, 1165, 1166, 1169, 1170], "branches": [[1149, 1150], [1150, 1151], [1150, 1156], [1157, 1158], [1157, 1163], [1158, 1159], [1158, 1161], [1163, 1164], [1164, 1165], [1164, 1169]]}
# gained: {"lines": [1131, 1133, 1150, 1151, 1152, 1156, 1157, 1158, 1159, 1161, 1164, 1165, 1166, 1169, 1170], "branches": [[1149, 1150], [1150, 1151], [1150, 1156], [1157, 1158], [1157, 1163], [1158, 1159], [1158, 1161], [1163, 1164], [1164, 1165], [1164, 1169]]}

import os
from datetime import datetime
import platform
import pytest

from aider.coders.base_coder import Coder


class DummyIO:
    def __init__(self):
        self.pretty = False
        self.encoding = "utf-8"
        self.chat_history_file = "nonexistent_history.md"
        # track warnings/outputs for assertions if needed
        self.warnings = []
        self.outputs = []

    def read_text(self, path):
        return ""

    def tool_warning(self, msg):
        self.warnings.append(msg)

    def tool_output(self, msg):
        self.outputs.append(msg)


class DummyWeakModel:
    def __init__(self):
        self.token_count = 0


class DummyModel:
    def __init__(self):
        self.reasoning_tag = None
        self.streaming = True
        self.cache_control = False
        self.use_repo_map = False
        self.weak_model = DummyWeakModel()
        self.max_chat_history_tokens = 10
        # info used in __init__
        self.info = {"max_input_tokens": None}

    def commit_message_models(self):
        return []


def test_get_platform_info_keyerror_and_auto_lint_auto_test(monkeypatch):
    # Arrange: make platform.platform raise KeyError to hit the except branch
    def raise_keyerror():
        raise KeyError()

    monkeypatch.setattr(platform, "platform", raise_keyerror)

    # Ensure the relevant shell environment variable is set
    shell_var = "COMSPEC" if os.name == "nt" else "SHELL"
    monkeypatch.setenv(shell_var, "/bin/fakeshell")

    io = DummyIO()
    main_model = DummyModel()

    coder = Coder(main_model, io, use_git=False, lint_cmds={"python": "flake8"}, auto_lint=True, test_cmd="pytest", auto_test=True)

    # Ensure get_user_language returns None to skip Language line
    monkeypatch.setattr(coder, "get_user_language", lambda: None)

    # Ensure repo True to include repo line
    coder.repo = True

    # Act
    platform_text = coder.get_platform_info()

    # Assert: Platform keyerror branch
    assert platform_text.startswith("- Platform information unavailable\n")
    # Shell line present with our env var
    assert f"- Shell: {shell_var}=/bin/fakeshell\n" in platform_text
    # Language should not be present
    assert "- Language:" not in platform_text
    # Current date present and correctly formatted
    expected_date = datetime.now().astimezone().strftime("%Y-%m-%d")
    assert f"- Current date: {expected_date}\n" in platform_text
    # Repo line present
    assert "- The user is operating inside a git repository\n" in platform_text
    # auto_lint header present
    assert "The user's pre-commit runs these lint commands" in platform_text
    # lint command listed with language
    assert "  - python: flake8\n" in platform_text
    # auto_test header present and test command appended
    assert "The user's pre-commit runs this test command, don't suggest running them: " in platform_text
    assert platform_text.endswith("pytest\n")


def test_get_platform_info_normal_platform_lang_and_prefixed_lint_and_test(monkeypatch):
    # Arrange: normal platform.platform value
    monkeypatch.setattr(platform, "platform", lambda: "MyOS-99")

    # Ensure the relevant shell environment variable is set
    shell_var = "COMSPEC" if os.name == "nt" else "SHELL"
    monkeypatch.setenv(shell_var, "/bin/othershell")

    io = DummyIO()
    main_model = DummyModel()

    # Set attributes to trigger lint_cmds with None key and auto_lint False,
    # and test_cmd with auto_test False
    coder = Coder(main_model, io, use_git=False, lint_cmds={None: "custom-lint"}, auto_lint=False, test_cmd="nose", auto_test=False)

    # Ensure get_user_language returns a value to include Language line
    monkeypatch.setattr(coder, "get_user_language", lambda: "fr-FR")

    # Ensure repo False
    coder.repo = False

    # Act
    platform_text = coder.get_platform_info()

    # Assert: Platform normal branch
    assert "- Platform: MyOS-99\n" in platform_text
    # Shell line present with our env var
    assert f"- Shell: {shell_var}=/bin/othershell\n" in platform_text
    # Language line present
    assert "- Language: fr-FR\n" in platform_text
    # Current date present and correctly formatted
    expected_date = datetime.now().astimezone().strftime("%Y-%m-%d")
    assert f"- Current date: {expected_date}\n" in platform_text
    # Repo line should NOT be present
    assert "- The user is operating inside a git repository\n" not in platform_text
    # auto_lint False header present
    assert "- The user prefers these lint commands:\n" in platform_text
    # lint command listed without language (lang is None)
    assert "  - custom-lint\n" in platform_text
    # auto_test False header present and test command appended
    assert "- The user prefers this test command: " in platform_text
    assert platform_text.endswith("nose\n")
