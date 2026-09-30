import asyncio
import types

import pytest

from pr_agent.servers import gitlab_webhook

# Helper stubs used across tests
class StubSettings:
    def __init__(self, disable_auto_feedback=False, commands=None):
        self.config = types.SimpleNamespace(disable_auto_feedback=disable_auto_feedback)
        self._commands = commands or []
        self.calls = []

    def get(self, key, default=None):
        self.calls.append(("get", key))
        return self._commands

    def set(self, key, value):
        self.calls.append(("set", key, value))


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.errors = []
        self.contexts = []

    def info(self, msg, **kwargs):
        self.infos.append((msg, kwargs))

    def error(self, msg):
        self.errors.append(msg)

    def contextualize(self, **kwargs):
        # Return a simple context manager compatible with `with`
        self.contexts.append(kwargs)

        class Ctx:
            def __enter__(self_in):
                return None

            def __exit__(self_in, exc_type, exc, tb):
                return False

        return Ctx()


class DummyAgent:
    def __init__(self, raise_exc=False):
        self.calls = []
        self.raise_exc = raise_exc

    async def handle_request(self, api_url, new_command):
        self.calls.append((api_url, new_command))
        if self.raise_exc:
            raise RuntimeError("boom")


# Tests

def test_skip_due_to_disable_auto_feedback_round_108(monkeypatch):
    """When commands_conf is 'pr_commands' and disable_auto_feedback is True,
    the function should log the auto-feedback skip and return early without
    calling should_process_pr_logic or fetching commands."""
    stub_settings = StubSettings(disable_auto_feedback=True, commands=["should_not_be_used"])
    logger = DummyLogger()

    # Patch functions in the module under test
    monkeypatch.setattr(gitlab_webhook, "apply_repo_settings", lambda api_url: None)
    monkeypatch.setattr(gitlab_webhook, "get_settings", lambda: stub_settings)
    monkeypatch.setattr(gitlab_webhook, "get_logger", lambda: logger)

    # If this is called, the test should fail because the early-return should happen
    def _fail_if_called(data):
        raise AssertionError("should_process_pr_logic should not be called when auto-feedback is disabled")

    monkeypatch.setattr(gitlab_webhook, "should_process_pr_logic", _fail_if_called)

    # Run the coro
    asyncio.run(gitlab_webhook._perform_commands_gitlab("pr_commands", DummyAgent(), "url", {"k": "v"}, {"some": "data"}))

    # Assert logger recorded the skip message and no settings.get/set calls other than those inspected
    assert any("Auto feedback is disabled" in msg for msg, _ in logger.infos)
    assert all(call[0] != "get" for call in stub_settings.calls)


def test_skip_due_to_should_process_pr_logic_false_round_108(monkeypatch):
    """When should_process_pr_logic returns False the function should return early
    and not fetch or set commands."""
    stub_settings = StubSettings(disable_auto_feedback=False, commands=["dont_run"])
    logger = DummyLogger()

    monkeypatch.setattr(gitlab_webhook, "apply_repo_settings", lambda api_url: None)
    monkeypatch.setattr(gitlab_webhook, "get_settings", lambda: stub_settings)
    monkeypatch.setattr(gitlab_webhook, "get_logger", lambda: logger)

    # should_process_pr_logic returning False should cause early return
    monkeypatch.setattr(gitlab_webhook, "should_process_pr_logic", lambda data: False)

    asyncio.run(gitlab_webhook._perform_commands_gitlab("some_conf", DummyAgent(), "url2", {}, {"a": 1}))

    # No get called to fetch commands and no set called to mark auto-command
    assert all(call[0] != "get" for call in stub_settings.calls)
    assert all(call[0] != "set" for call in stub_settings.calls)


def test_perform_commands_success_round_108(monkeypatch):
    """When commands are present and the agent handles requests successfully,
    the agent.handle_request should be awaited with the transformed new_command
    and the settings should be updated to indicate auto-command."""
    commands = ["doit a b"]
    stub_settings = StubSettings(disable_auto_feedback=False, commands=commands)
    logger = DummyLogger()

    # Make update_settings_from_args produce a predictable change
    monkeypatch.setattr(gitlab_webhook, "update_settings_from_args", lambda args: ["--opt"])
    monkeypatch.setattr(gitlab_webhook, "apply_repo_settings", lambda api_url: None)
    monkeypatch.setattr(gitlab_webhook, "get_settings", lambda: stub_settings)
    monkeypatch.setattr(gitlab_webhook, "get_logger", lambda: logger)
    monkeypatch.setattr(gitlab_webhook, "should_process_pr_logic", lambda data: True)

    agent = DummyAgent(raise_exc=False)

    asyncio.run(gitlab_webhook._perform_commands_gitlab("gitlab_commands", agent, "http://api", {"ctx": "v"}, {"pr": "data"}))

    # After running, settings.set should have been called to mark auto-command
    assert ("set", "config.is_auto_command", True) in stub_settings.calls or any(c[0] == "set" and c[1] == "config.is_auto_command" for c in stub_settings.calls)

    # Agent should have been called with the joined new_command (command + other_args)
    assert agent.calls == [("http://api", "doit --opt")]
    # And logger should have recorded a Performing command info
    assert any("Performing command" in msg for msg, _ in logger.infos)


def test_perform_commands_exception_round_108(monkeypatch):
    """If agent.handle_request raises, the exception branch should log an error
    containing the command name and exception message."""
    commands = ["fail arg1 arg2"]
    stub_settings = StubSettings(disable_auto_feedback=False, commands=commands)
    logger = DummyLogger()

    monkeypatch.setattr(gitlab_webhook, "update_settings_from_args", lambda args: ["--x"])
    monkeypatch.setattr(gitlab_webhook, "apply_repo_settings", lambda api_url: None)
    monkeypatch.setattr(gitlab_webhook, "get_settings", lambda: stub_settings)
    monkeypatch.setattr(gitlab_webhook, "get_logger", lambda: logger)
    monkeypatch.setattr(gitlab_webhook, "should_process_pr_logic", lambda data: True)

    # Agent will raise when handling the request to hit the exception logging branch
    agent = DummyAgent(raise_exc=True)

    asyncio.run(gitlab_webhook._perform_commands_gitlab("gitlab_commands", agent, "api-url", {}, {}))

    # The error log should reference the command name 'fail' and the exception string 'boom'
    assert any("Failed to perform command" in err and "fail" in err and "boom" in err for err in logger.errors)
