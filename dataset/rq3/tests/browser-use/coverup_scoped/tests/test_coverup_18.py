# file: browser_use/cli.py:1488-1608
# asked: {"lines": [1488, 1491, 1494, 1497, 1503, 1504, 1505, 1507, 1509, 1510, 1513, 1516, 1517, 1518, 1519, 1520, 1521, 1522, 1527, 1530, 1532, 1534, 1535, 1536, 1540, 1541, 1542, 1543, 1544, 1545, 1548, 1553, 1554, 1556, 1557, 1559, 1562, 1563, 1564, 1565, 1566, 1567, 1568, 1569, 1573, 1574, 1576, 1577, 1578, 1579, 1580, 1581, 1582, 1583, 1584, 1587, 1588, 1590, 1592, 1593, 1596, 1599, 1602, 1603, 1604, 1607, 1608], "branches": [[1553, 1554], [1553, 1562], [1587, 1588], [1587, 1592], [1603, 1604], [1603, 1607], [1607, 0], [1607, 1608]]}
# gained: {"lines": [1488, 1491, 1494, 1497, 1503, 1504, 1505, 1507, 1509, 1510, 1513, 1516, 1517, 1518, 1519, 1520, 1521, 1522, 1527, 1530, 1532, 1534, 1535, 1536, 1540, 1541, 1542, 1543, 1544, 1545, 1548, 1553, 1554, 1556, 1562, 1563, 1564, 1565, 1566, 1567, 1568, 1569, 1573, 1574, 1576, 1577, 1578, 1579, 1580, 1581, 1582, 1583, 1584, 1587, 1592, 1593, 1596, 1599, 1602, 1603, 1607], "branches": [[1553, 1554], [1587, 1592], [1603, 1607], [1607, 0]]}

import asyncio
import types
import sys
import click
import pytest
import importlib

@pytest.mark.asyncio
async def test_run_prompt_mode_success(monkeypatch):
    # Import the module under test
    cli = importlib.import_module('browser_use.cli')

    # Ensure logging_config.setup_logging import inside function works but is a no-op
    logging_mod = types.ModuleType("browser_use.logging_config")
    def setup_logging():
        # simulate real setup without side effects
        return None
    logging_mod.setup_logging = setup_logging
    monkeypatch.setitem(sys.modules, 'browser_use.logging_config', logging_mod)

    # Fake telemetry to capture calls
    class FakeTelemetry:
        def __init__(self):
            self.captured = []
            self.flushed = False
        def capture(self, event):
            self.captured.append(event)
        def flush(self):
            self.flushed = True

    fake_telemetry = FakeTelemetry()
    monkeypatch.setattr(cli, 'ProductTelemetry', lambda: fake_telemetry)

    # Fake get_browser_use_version
    monkeypatch.setattr(cli, 'get_browser_use_version', lambda: 'v1.2.3')

    # Provide USER_DATA_DIR
    monkeypatch.setattr(cli, 'USER_DATA_DIR', '/tmp/browser_use_test')

    # Monkeypatch load_user_config and update_config_with_click_args
    monkeypatch.setattr(cli, 'load_user_config', lambda: {'agent': {}, 'browser': {}})
    monkeypatch.setattr(cli, 'update_config_with_click_args', lambda config, ctx: config)

    # Fake LLM
    class FakeLLM:
        model = 'fake-model'
    monkeypatch.setattr(cli, 'get_llm', lambda config: FakeLLM())

    # Fake BrowserProfile to accept arbitrary kwargs
    class FakeProfile:
        def __init__(self, user_data_dir=None, **kwargs):
            self.user_data_dir = user_data_dir
            self.kwargs = kwargs
    monkeypatch.setattr(cli, 'BrowserProfile', FakeProfile)

    # Fake BrowserSession with kill recording
    class FakeBrowserSession:
        def __init__(self, browser_profile=None):
            self.browser_profile = browser_profile
            self.killed = False
        async def kill(self):
            self.killed = True
    monkeypatch.setattr(cli, 'BrowserSession', FakeBrowserSession)

    # Fake Agent whose run is awaited
    class FakeAgent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.ran = False
        async def run(self):
            self.ran = True
    monkeypatch.setattr(cli, 'Agent', lambda **kwargs: FakeAgent(**kwargs))

    # Prevent actual sleeping and cancelling external tasks: make sleep immediate
    async def fake_sleep(duration):
        return None
    monkeypatch.setattr(cli.asyncio, 'sleep', fake_sleep)

    # Ensure asyncio.all_tasks returns only the current task to avoid cancelling external tasks
    def fake_all_tasks():
        cur = asyncio.current_task()
        return {cur} if cur is not None else set()
    monkeypatch.setattr(cli.asyncio, 'all_tasks', fake_all_tasks)

    # Prepare a minimal click.Context
    ctx = click.Context(click.Command('testcmd'))

    # Run the function
    await cli.run_prompt_mode("do something", ctx, debug=False)

    # Assertions: telemetry captured start and task_completed
    actions = [getattr(ev, 'action', None) if hasattr(ev, 'action') else getattr(ev, 'action', None) for ev in fake_telemetry.captured]
    # Because CLITelemetryEvent may be any object, check by attribute existence or string presence
    # If CLITelemetryEvent is an object with 'action' attribute, use it, else fallback to string repr
    extracted_actions = []
    for ev in fake_telemetry.captured:
        if hasattr(ev, 'action'):
            extracted_actions.append(ev.action)
        else:
            extracted_actions.append(str(ev))
    assert 'start' in extracted_actions
    assert 'task_completed' in extracted_actions
    assert fake_telemetry.flushed is True

@pytest.mark.asyncio
async def test_run_prompt_mode_exception(monkeypatch, capsys):
    # Import module
    cli = importlib.import_module('browser_use.cli')

    # Ensure logging_config.setup_logging import inside function works but is a no-op
    logging_mod = types.ModuleType("browser_use.logging_config")
    def setup_logging():
        return None
    logging_mod.setup_logging = setup_logging
    monkeypatch.setitem(sys.modules, 'browser_use.logging_config', logging_mod)

    # Fake telemetry to capture calls
    class FakeTelemetry:
        def __init__(self):
            self.captured = []
            self.flushed = False
        def capture(self, event):
            self.captured.append(event)
        def flush(self):
            self.flushed = True
    fake_telemetry = FakeTelemetry()
    monkeypatch.setattr(cli, 'ProductTelemetry', lambda: fake_telemetry)

    # Fake get_browser_use_version
    monkeypatch.setattr(cli, 'get_browser_use_version', lambda: 'vX')

    # USER_DATA_DIR
    monkeypatch.setattr(cli, 'USER_DATA_DIR', '/tmp/browser_use_test')

    # Have load_user_config and update_config_with_click_args succeed
    monkeypatch.setattr(cli, 'load_user_config', lambda: {'agent': {}, 'browser': {}})
    monkeypatch.setattr(cli, 'update_config_with_click_args', lambda config, ctx: config)

    # Fake LLM
    class FakeLLM:
        model = 'err-model'
    monkeypatch.setattr(cli, 'get_llm', lambda config: FakeLLM())

    # Fake BrowserProfile and BrowserSession as before
    class FakeProfile:
        def __init__(self, user_data_dir=None, **kwargs):
            self.user_data_dir = user_data_dir
            self.kwargs = kwargs
    monkeypatch.setattr(cli, 'BrowserProfile', FakeProfile)

    class FakeBrowserSession:
        def __init__(self, browser_profile=None):
            self.browser_profile = browser_profile
            self.killed = False
        async def kill(self):
            self.killed = True
    monkeypatch.setattr(cli, 'BrowserSession', FakeBrowserSession)

    # Fake Agent whose run raises an exception
    class BadAgent:
        def __init__(self, **kwargs):
            pass
        async def run(self):
            raise RuntimeError("boom")
    monkeypatch.setattr(cli, 'Agent', lambda **kwargs: BadAgent(**kwargs))

    # Prevent actual sleeping and cancelling external tasks
    async def fake_sleep(duration):
        return None
    monkeypatch.setattr(cli.asyncio, 'sleep', fake_sleep)

    def fake_all_tasks():
        cur = asyncio.current_task()
        return {cur} if cur is not None else set()
    monkeypatch.setattr(cli.asyncio, 'all_tasks', fake_all_tasks)

    # Prepare ctx
    ctx = click.Context(click.Command('testcmd'))

    # Run and expect SystemExit
    with pytest.raises(SystemExit) as excinfo:
        await cli.run_prompt_mode("will fail", ctx, debug=False)

    assert excinfo.value.code == 1

    # stderr should contain the error message
    captured = capsys.readouterr()
    assert "Error: boom" in captured.err

    # Telemetry should have recorded start and error
    extracted_actions = []
    for ev in fake_telemetry.captured:
        if hasattr(ev, 'action'):
            extracted_actions.append(ev.action)
        else:
            extracted_actions.append(str(ev))
    assert 'start' in extracted_actions
    assert 'error' in extracted_actions
    assert fake_telemetry.flushed is True
