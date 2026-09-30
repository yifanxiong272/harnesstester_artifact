import asyncio
import contextlib
import types

import pr_agent.servers.azuredevops_server_webhook as webhook


class FakeLogger:
    def __init__(self):
        self.infos = []
        self.errors = []
        self.contexts = []

    def info(self, msg, **kwargs):
        # store raw message for assertions
        self.infos.append((msg, kwargs))

    def error(self, msg, **kwargs):
        self.errors.append((msg, kwargs))

    @contextlib.contextmanager
    def contextualize(self, **kwargs):
        # record that contextualize was entered with these kwargs
        self.contexts.append(kwargs)
        yield


class FakeSettings:
    def __init__(self, commands=None, disable_auto_feedback=False):
        # commands is the value returned by get_settings().get(...)
        self._commands = commands
        self.config = types.SimpleNamespace(disable_auto_feedback=disable_auto_feedback)
        self.set_calls = []
        self.get_called = False

    def get(self, key):
        # record the call and return configured commands
        self.get_called = True
        return self._commands

    def set(self, key, value):
        self.set_calls.append((key, value))


class FakeAgent:
    def __init__(self, raise_on_call=False):
        self.calls = []
        self.raise_on_call = raise_on_call

    async def handle_request(self, api_url, new_command):
        # mimic async handling, record the invocation
        self.calls.append((api_url, new_command))
        if self.raise_on_call:
            raise ValueError("boom")


# Tests

def test_auto_feedback_disabled_round_101(monkeypatch):
    """
    When commands_conf == 'pr_commands' and auto feedback is disabled,
    the function should log an info message and return early without
    calling get_settings().get(...).
    """
    fake_logger = FakeLogger()
    # settings where disable_auto_feedback is True
    fake_settings = FakeSettings(commands=["should_not_be_used"], disable_auto_feedback=True)

    # Patch dependencies in the module under test
    monkeypatch.setattr(webhook, "apply_repo_settings", lambda api_url: None)
    monkeypatch.setattr(webhook, "get_logger", lambda: fake_logger)
    # get_settings should return our settings object
    monkeypatch.setattr(webhook, "get_settings", lambda: fake_settings)

    # Run the coroutine
    asyncio.run(webhook._perform_commands_azure("pr_commands", FakeAgent(), "https://api.example", {"ctx": 1}))

    # Assert logger was invoked with the auto feedback disabled message
    assert any("Auto feedback is disabled" in msg for msg, _ in fake_logger.infos)
    # Ensure get(...) was not called when skipping
    assert fake_settings.get_called is False


def test_no_commands_round_101(monkeypatch):
    """
    When settings.get(...) returns falsy (None/empty), the function should
    return early and should not set the auto-command flag.
    """
    fake_logger = FakeLogger()
    fake_settings = FakeSettings(commands=None, disable_auto_feedback=False)

    monkeypatch.setattr(webhook, "apply_repo_settings", lambda api_url: None)
    monkeypatch.setattr(webhook, "get_logger", lambda: fake_logger)
    monkeypatch.setattr(webhook, "get_settings", lambda: fake_settings)

    asyncio.run(webhook._perform_commands_azure("some_conf", FakeAgent(), "https://api.example", {"ctx": 2}))

    # Should have called get(...) once and returned before setting anything
    assert fake_settings.get_called is True
    assert fake_settings.set_calls == []
    # No performing messages should be logged
    assert not any("Performing command" in msg for msg, _ in fake_logger.infos)


def test_perform_commands_success_round_101(monkeypatch):
    """
    When there are commands, the function should set the config.is_auto_command flag,
    call update_settings_from_args, log performing message, enter contextualize, and
    call agent.handle_request with the reconstructed command.
    """
    fake_logger = FakeLogger()
    # Provide one command that will be split
    fake_settings = FakeSettings(commands=["doit oldarg"], disable_auto_feedback=False)

    # update_settings_from_args should transform args deterministically
    def fake_update_settings_from_args(args):
        # pretend it replaces oldarg with newarg
        return [a + "-new" for a in args]

    agent = FakeAgent(raise_on_call=False)

    monkeypatch.setattr(webhook, "apply_repo_settings", lambda api_url: None)
    monkeypatch.setattr(webhook, "get_logger", lambda: fake_logger)
    monkeypatch.setattr(webhook, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(webhook, "update_settings_from_args", fake_update_settings_from_args)

    asyncio.run(webhook._perform_commands_azure("commands", agent, "https://api.example", {"ctx": 3}))

    # settings.set should have been called to mark auto command
    assert ("config.is_auto_command", True) in fake_settings.set_calls

    # The agent should have been called with the reconstructed command 'doit oldarg-new'
    assert agent.calls == [("https://api.example", "doit oldarg-new")]

    # A performing message should have been logged
    assert any("Performing command" in msg for msg, _ in fake_logger.infos)

    # Contextualize should have been entered once
    assert len(fake_logger.contexts) == 1


def test_perform_commands_exception_round_101(monkeypatch):
    """
    If agent.handle_request raises, the function should catch it and log an error
    that includes the command name and the exception message.
    """
    fake_logger = FakeLogger()
    fake_settings = FakeSettings(commands=["doit crasharg"], disable_auto_feedback=False)

    def identity_update(args):
        return args

    # Agent that raises when called
    agent = FakeAgent(raise_on_call=True)

    monkeypatch.setattr(webhook, "apply_repo_settings", lambda api_url: None)
    monkeypatch.setattr(webhook, "get_logger", lambda: fake_logger)
    monkeypatch.setattr(webhook, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(webhook, "update_settings_from_args", identity_update)

    asyncio.run(webhook._perform_commands_azure("commands", agent, "https://api.example", {"ctx": 4}))

    # An error log should have been produced mentioning the command and the exception
    assert any("Failed to perform command doit" in msg and "boom" in msg for msg, _ in fake_logger.errors)
