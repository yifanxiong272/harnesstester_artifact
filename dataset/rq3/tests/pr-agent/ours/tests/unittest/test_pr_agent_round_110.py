import asyncio
import pytest
import importlib

from types import SimpleNamespace

MODULE_PATH = "pr_agent.agent.pr_agent"


class _CM:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []
        self.errors = []

    def info(self, *a, **k):
        self.infos.append((a, k))

    def warning(self, *a, **k):
        self.warnings.append((a, k))

    def error(self, *a, **k):
        self.errors.append((a, k))

    def contextualize(self, **kw):
        return _CM()


class DynaboxFake:
    __module__ = "dynaconf.utils.boxing"
    __name__ = "DynaBox"


class FakeSettingHolder:
    def __init__(self, extra_instructions):
        # instance of a class whose type() string matches the dynabox repr
        cls = type("DynaBox", (), {})
        cls.__module__ = "dynaconf.utils.boxing"
        cls.__name__ = "DynaBox"
        self.__class__ = cls
        # attribute the code checks
        self.extra_instructions = extra_instructions


class FakeSettings:
    def __init__(self, mapping, response_language="fr-FR"):
        # mapping: key -> FakeSettingHolder
        self._mapping = dict(mapping)
        self.config = {"response_language": response_language}

    def __iter__(self):
        return iter(self._mapping.keys())

    def get(self, key, default=None):
        return self._mapping.get(key, default)


class FakePRReviewer:
    def __init__(self, pr_url, is_answer=False, is_auto=False, args=None, ai_handler=None):
        self.pr_url = pr_url
        self.is_answer = is_answer
        self.is_auto = is_auto
        self.args = args
        self.ai_handler = ai_handler
        self.ran = False

    async def run(self):
        # simulate some async work
        await asyncio.sleep(0)
        self.ran = True


class FakeCommand:
    def __init__(self, pr_url, ai_handler=None, args=None):
        self.pr_url = pr_url
        self.ai_handler = ai_handler
        self.args = args
        self.ran = False

    async def run(self):
        await asyncio.sleep(0)
        self.ran = True


@pytest.mark.asyncio
async def test_handle_request_adds_instruction_when_empty_round_110(monkeypatch):
    """
    Verify that when response_language != 'en-us' and a DynaBox-style setting
    has no existing extra_instructions (None/empty), the language instruction
    is set exactly to the lang_instruction_text (no separator appended).
    """
    mod = importlib.import_module(MODULE_PATH)

    # Patch environment functions and vars used by _handle_request
    monkeypatch.setattr(mod, "apply_repo_settings", lambda pr_url: None)
    monkeypatch.setattr(mod, "update_settings_from_args", lambda args: args)
    monkeypatch.setattr(mod, "CliArgs", SimpleNamespace(validate_user_args=lambda args: (True, None)))

    fake_logger = FakeLogger()
    monkeypatch.setattr(mod, "get_logger", lambda: fake_logger)

    # Create settings with one key whose setting.extra_instructions is None (empty case)
    holder = FakeSettingHolder(extra_instructions=None)
    fake_settings = FakeSettings({"repo": holder}, response_language="fr-FR")
    monkeypatch.setattr(mod, "get_settings", lambda: fake_settings)

    # Ensure other symbols benign
    monkeypatch.setattr(mod, "PRReviewer", FakePRReviewer)
    monkeypatch.setattr(mod, "command2class", {})

    # Create agent and call the handler with an unknown command to return False, but
    # after the settings modification block runs
    PRAgent = getattr(mod, "PRAgent")
    agent = PRAgent(ai_handler=None)

    result = await agent._handle_request("http://x", ["unknown_cmd", "x"], notify=None)

    assert result is False, "Unknown command should return False"

    # Build the expected language instruction exactly as in source
    lang_instruction_text = (
        "Your response MUST be written in the language corresponding to locale code: 'fr-FR'. This is crucial."
    )

    assert holder.extra_instructions == lang_instruction_text


@pytest.mark.asyncio
async def test_handle_request_appends_instruction_when_existing_round_110(monkeypatch):
    """
    Verify that when extra_instructions exists (non-empty string) the lang instruction
    is appended with the separator_text and that handler returns True when a valid
    command from command2class runs successfully and notify is called.
    """
    mod = importlib.import_module(MODULE_PATH)

    monkeypatch.setattr(mod, "apply_repo_settings", lambda pr_url: None)
    monkeypatch.setattr(mod, "update_settings_from_args", lambda args: args)
    monkeypatch.setattr(mod, "CliArgs", SimpleNamespace(validate_user_args=lambda args: (True, None)))

    fake_logger = FakeLogger()
    monkeypatch.setattr(mod, "get_logger", lambda: fake_logger)

    # existing instructions (non-empty), so append path should be taken
    holder = FakeSettingHolder(extra_instructions="Existing instructions.")
    fake_settings = FakeSettings({"repo": holder}, response_language="fr-FR")
    monkeypatch.setattr(mod, "get_settings", lambda: fake_settings)

    # Wire command2class to include a command that will be executed
    monkeypatch.setattr(mod, "PRReviewer", FakePRReviewer)
    monkeypatch.setattr(mod, "command2class", {"somecmd": FakeCommand})

    PRAgent = getattr(mod, "PRAgent")
    agent = PRAgent(ai_handler=None)

    notified = []

    def notify_func():
        notified.append(True)

    # call with the command present in command2class so the mapped command runs
    result = await agent._handle_request("http://x", ["somecmd", "arg1"], notify=notify_func)

    assert result is True
    assert notified == [True], "notify should have been called once"

    lang_instruction_text = (
        "Your response MUST be written in the language corresponding to locale code: 'fr-FR'. This is crucial."
    )
    separator_text = "\n======\n\nIn addition, "

    assert holder.extra_instructions == "Existing instructions." + separator_text + lang_instruction_text


@pytest.mark.asyncio
async def test_handle_request_no_duplicate_instruction_round_110(monkeypatch):
    """
    If the lang instruction is already part of extra_instructions, ensure nothing is changed.
    """
    mod = importlib.import_module(MODULE_PATH)

    monkeypatch.setattr(mod, "apply_repo_settings", lambda pr_url: None)
    monkeypatch.setattr(mod, "update_settings_from_args", lambda args: args)
    monkeypatch.setattr(mod, "CliArgs", SimpleNamespace(validate_user_args=lambda args: (True, None)))

    fake_logger = FakeLogger()
    monkeypatch.setattr(mod, "get_logger", lambda: fake_logger)

    lang_instruction_text = (
        "Your response MUST be written in the language corresponding to locale code: 'fr-FR'. This is crucial."
    )

    # Put the lang_instruction_text already inside extra_instructions
    holder = FakeSettingHolder(extra_instructions="prefix\n" + lang_instruction_text + "\nsuffix")
    fake_settings = FakeSettings({"repo": holder}, response_language="fr-FR")
    monkeypatch.setattr(mod, "get_settings", lambda: fake_settings)

    monkeypatch.setattr(mod, "PRReviewer", FakePRReviewer)
    monkeypatch.setattr(mod, "command2class", {})

    PRAgent = getattr(mod, "PRAgent")
    agent = PRAgent(ai_handler=None)

    res = await agent._handle_request("http://x", ["unknown_cmd", "x"], notify=None)

    assert res is False
    # Should remain unchanged because the lang instruction was already present
    assert "Your response MUST be written in the language corresponding to locale code: 'fr-FR'" in holder.extra_instructions
