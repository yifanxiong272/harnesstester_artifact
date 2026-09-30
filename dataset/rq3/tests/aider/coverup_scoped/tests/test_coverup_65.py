# file: aider/coders/base_coder.py:1174-1224
# asked: {"lines": [1179, 1183, 1192, 1193, 1194, 1196, 1199], "branches": [[1178, 1179], [1182, 1183], [1187, 1192], [1198, 1199]]}
# gained: {"lines": [1179, 1183, 1199], "branches": [[1178, 1179], [1182, 1183], [1198, 1199]]}

import types
import pytest

from aider.coders.base_coder import Coder


class DummyModel:
    def __init__(self, lazy=False, overeager=False, streaming=True, info=None):
        self.lazy = lazy
        self.overeager = overeager
        self.streaming = streaming
        self.info = info or {}


class DummyPrompts:
    def __init__(self):
        self.lazy_prompt = "LAZY_PROMPT"
        self.overeager_prompt = "OVEREAGER_PROMPT"
        self.shell_cmd_prompt = "SHELL_CMD_PROMPT for {platform}"
        self.shell_cmd_reminder = "SHELL_CMD_REMINDER for {platform}"
        self.rename_with_shell = "RENAME_WITH_SHELL"
        self.no_shell_cmd_prompt = "NO_SHELL_CMD_PROMPT for {platform}"
        self.no_shell_cmd_reminder = "NO_SHELL_CMD_REMINDER for {platform}"
        self.go_ahead_tip = "GO_AHEAD_TIP"


def make_coder_instance(main_model, gpt_prompts, suggest_shell_commands=True, fence=None):
    # Create Coder instance without running __init__ to avoid heavy setup.
    coder = Coder.__new__(Coder)
    coder.main_model = main_model
    coder.gpt_prompts = gpt_prompts
    coder.suggest_shell_commands = suggest_shell_commands
    # If fence not provided, default to triple backticks string
    if fence is None:
        fence = "`" * 3
    coder.fence = fence
    return coder


def test_fmt_system_prompt_overeager_and_user_lang():
    prompts = DummyPrompts()
    model = DummyModel(lazy=False, overeager=True)
    coder = make_coder_instance(model, prompts, suggest_shell_commands=True, fence="`" * 3)

    coder.get_user_language = types.MethodType(lambda self: "Spanish", coder)
    coder.get_platform_info = types.MethodType(lambda self: "linux-x86_64", coder)

    template = (
        "FINAL_REMINDERS:[{final_reminders}]|SHELL_PROMPT:[{shell_cmd_prompt}]|"
        "SHELL_REMINDER:[{shell_cmd_reminder}]|RENAME:[{rename_with_shell}]|"
        "GO_AHEAD:[{go_ahead_tip}]|LANG:[{language}]|QUAD:[{quad_backtick_reminder}]|PLAT:[{platform}]"
    )

    result = Coder.fmt_system_prompt(coder, template)

    assert "OVEREAGER_PROMPT" in result
    assert "Reply in Spanish." in result
    assert "SHELL_CMD_PROMPT for linux-x86_64" in result
    assert "SHELL_CMD_REMINDER for linux-x86_64" in result
    assert "RENAME_WITH_SHELL" in result
    assert "GO_AHEAD_TIP" in result
    assert "quadruple" not in result


def test_fmt_system_prompt_no_shell_and_no_user_lang_quad_fence():
    prompts = DummyPrompts()
    model = DummyModel(lazy=False, overeager=False)
    # Use a sequence where fence[0] == "