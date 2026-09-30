# file: pr_agent/cli.py:69-101
# asked: {"lines": [69, 70, 71, 72, 73, 74, 75, 77, 78, 80, 81, 82, 84, 86, 88, 89, 90, 91, 92, 93, 94, 97, 99, 100, 101], "branches": [[71, 72], [71, 73], [73, 74], [73, 77], [81, 82], [81, 84], [86, 88], [86, 97], [90, 91], [90, 97], [92, 93], [92, 97], [100, 0], [100, 101]]}
# gained: {"lines": [69, 70, 71, 72, 73, 74, 75, 77, 78, 80, 81, 82, 84, 86, 88, 89, 90, 91, 92, 93, 94, 97, 99, 100, 101], "branches": [[71, 72], [71, 73], [73, 74], [73, 77], [81, 82], [81, 84], [86, 88], [90, 91], [90, 97], [92, 93], [100, 0], [100, 101]]}

import asyncio
from types import SimpleNamespace
import builtins
import pytest

import pr_agent.cli as cli_module


class DummyParser:
    def __init__(self, args_obj):
        self._args = args_obj
        self.printed = False

    def parse_args(self, inargs=None):
        return self._args

    def print_help(self):
        self.printed = True


class DummySettings:
    def __init__(self, litellm=None):
        self._cli_mode_set = False
        self.litellm = litellm or {}

    def set(self, key, val):
        if key == "CONFIG.CLI_MODE":
            self._cli_mode_set = val


class DummyLogger:
    def __init__(self):
        self.debug_calls = []
        self.warning_calls = []

    def debug(self, *args, **kwargs):
        self.debug_calls.append((args, kwargs))

    def warning(self, *args, **kwargs):
        self.warning_calls.append((args, kwargs))


class DummyPRAgent:
    def __init__(self, handle_coro):
        # handle_coro should be an async function taking (url, rest)
        self._handle = handle_coro

    async def handle_request(self, url, rest):
        return await self._handle(url, rest)


@pytest.mark.parametrize("inargs", [None, []])
def test_run_no_urls_print_help(monkeypatch, inargs):
    # setup parser to return args with no urls
    args = SimpleNamespace(pr_url=None, issue_url=None, command=None, rest=[])
    parser = DummyParser(args)
    monkeypatch.setattr(cli_module, "set_parser", lambda: parser)
    # Run
    result = cli_module.run(inargs=inargs)
    # Should have called print_help and returned None
    assert parser.printed is True
    assert result is None


def test_run_issue_url_with_callbacks_no_pending(monkeypatch):
    # args with issue_url set
    args = SimpleNamespace(pr_url=None, issue_url="http://issue", command="DoIt", rest=[])
    parser = DummyParser(args)
    monkeypatch.setattr(cli_module, "set_parser", lambda: parser)

    # Dummy settings with enable_callbacks True
    settings = DummySettings(litellm={"enable_callbacks": True})
    monkeypatch.setattr(cli_module, "get_settings", lambda: settings)

    # Dummy logger to capture debug/warning
    logger = DummyLogger()
    monkeypatch.setattr(cli_module, "get_logger", lambda: logger)

    # PRAgent.handle_request returns a truthy result and does not create extra tasks
    async def handle_ok(url, rest):
        await asyncio.sleep(0)  # yield control
        return {"result": "ok"}

    monkeypatch.setattr(cli_module, "PRAgent", lambda: DummyPRAgent(handle_ok))

    # Ensure asyncio.all_tasks returns only the current task (no extra pending tasks)
    # Patch cli_module.asyncio.all_tasks to call real current all_tasks but it usually will only include current task.
    # No need to override asyncio.wait; it won't be used because tasks will be empty.
    # Run
    res = cli_module.run(args=args)
    # run() returns None, but ensure parser.print_help not called and CLI_MODE set
    assert parser.printed is False
    assert settings._cli_mode_set is True
    # Because enable_callbacks True and no extra tasks, debug should have been called
    assert any("Waiting for event queue to complete" in args[0][0] for args in logger.debug_calls)


def test_run_pr_url_with_pending_tasks_causes_warning_and_falsy_result_print_help(monkeypatch):
    # args with pr_url set and command lowercasing branch
    args = SimpleNamespace(pr_url="http://pr", issue_url=None, command="TEST", rest=[])
    parser = DummyParser(args)
    monkeypatch.setattr(cli_module, "set_parser", lambda: parser)

    # Dummy settings with enable_callbacks True
    settings = DummySettings(litellm={"enable_callbacks": True})
    monkeypatch.setattr(cli_module, "get_settings", lambda: settings)

    # Dummy logger to capture debug/warning
    logger = DummyLogger()
    monkeypatch.setattr(cli_module, "get_logger", lambda: logger)

    # Create a fake pending task object
    class FakeTask:
        def __init__(self, name="fake"):
            self._name = name

        def get_coro(self):
            return f"coro-{self._name}"

    fake_task = FakeTask()

    # Patch asyncio.all_tasks to include current task and the fake task
    # We'll reference the cli_module.asyncio.current_task at call time
    def fake_all_tasks():
        cur = cli_module.asyncio.current_task()
        return [cur, fake_task]

    monkeypatch.setattr(cli_module.asyncio, "all_tasks", fake_all_tasks)

    # Patch asyncio.wait used inside the module to return pending containing our fake_task quickly
    async def fake_wait(tasks, timeout=None):
        # simulate that the fake_task is pending
        return (set(), {fake_task})

    monkeypatch.setattr(cli_module.asyncio, "wait", fake_wait)

    # PRAgent.handle_request returns falsy result to trigger parser.print_help at end
    async def handle_false(url, rest):
        await asyncio.sleep(0)  # yield control
        return False

    monkeypatch.setattr(cli_module, "PRAgent", lambda: DummyPRAgent(handle_false))

    # Run
    res = cli_module.run(args=args)

    # After run, since result was falsy, parser.print_help should have been called
    assert parser.printed is True
    # CLI_MODE should have been set
    assert settings._cli_mode_set is True
    # The logger should have recorded the debug then a warning about pending tasks
    assert any("Waiting for event queue to complete" in args[0][0] for args in logger.debug_calls)
    assert len(logger.warning_calls) == 1
    # The warning message should mention callback tasks
    warn_msg = logger.warning_calls[0][0][0]
    assert "callback tasks" in warn_msg
