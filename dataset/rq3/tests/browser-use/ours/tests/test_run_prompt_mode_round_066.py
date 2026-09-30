import sys
import types
import importlib
from types import ModuleType
from pathlib import Path
import pytest

# All tests and helpers must end with _round_066 as required.

@pytest.mark.asyncio
async def test_run_prompt_mode_success_round_066():
    """Successful oneshot run: agent.run completes, browser_session.kill is awaited,
    telemetry start and task_completed events captured, and telemetry flushed.
    """
    # Load the module under test
    cli = importlib.import_module('browser_use.cli')

    # Provide a fake browser_use.logging_config module with setup_logging
    fake_logging_mod = ModuleType('browser_use.logging_config')
    called = {'setup_logging': False}

    def fake_setup_logging():
        called['setup_logging'] = True

    fake_logging_mod.setup_logging = fake_setup_logging
    sys.modules['browser_use.logging_config'] = fake_logging_mod

    # Fake telemetry classes and capture last instance for assertions
    class FakeTelemetry:
        last = None

        def __init__(self):
            FakeTelemetry.last = self
            self.captured = []
            self.flushed = False

        def capture(self, ev):
            self.captured.append(ev)

        def flush(self):
            self.flushed = True

    class FakeEvent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    cli.ProductTelemetry = FakeTelemetry
    cli.CLITelemetryEvent = FakeEvent

    # Fake config and LLM pipeline
    cli.load_user_config = lambda: { 'browser': {}, 'agent': {} }
    cli.update_config_with_click_args = lambda cfg, ctx: cfg

    class FakeLLM:
        def __init__(self):
            self.model = 'fake-model'

    cli.get_llm = lambda cfg: FakeLLM()

    # Fake AgentSettings with model_validate -> instance with model_dump
    class FakeAgentSettings:
        @classmethod
        def model_validate(cls, data):
            class SettingsObj:
                def model_dump(self):
                    return {}

            return SettingsObj()

    cli.AgentSettings = FakeAgentSettings

    # Fake BrowserProfile and BrowserSession; track last session instance
    class FakeProfile:
        pass

    cli.BrowserProfile = lambda user_data_dir, **kwargs: FakeProfile()

    class FakeBrowserSession:
        last = None

        def __init__(self, browser_profile=None):
            FakeBrowserSession.last = self
            self.killed = False

        async def kill(self):
            self.killed = True

    cli.BrowserSession = FakeBrowserSession

    # Fake Agent whose run completes normally
    class FakeAgent:
        def __init__(self, task, llm, browser_session, source, **kwargs):
            self.task = task
            self.llm = llm
            self.browser_session = browser_session
            self.source = source
            self.ran = False

        async def run(self):
            # simulate some asynchronous work but deterministic
            self.ran = True

    cli.Agent = FakeAgent

    # Prevent cancellation of real test tasks and make sleep no-op
    async def fake_sleep(duration):
        return None

    cli.asyncio.sleep = fake_sleep
    cli.asyncio.all_tasks = lambda: set()

    # Ensure USER_DATA_DIR exists and is stable
    cli.USER_DATA_DIR = Path('/tmp')

    # Run the function under test
    # ctx is only passed into update_config_with_click_args which we patched
    await cli.run_prompt_mode('do something', ctx=object(), debug=False)

    # Assertions
    # setup_logging should have been imported and invoked at least indirectly
    assert called['setup_logging'] is True

    # Telemetry instance should exist and have two captures: 'start' and 'task_completed'
    tel = FakeTelemetry.last
    assert tel is not None, 'Telemetry instance should have been created'
    # At least one 'start' and one 'task_completed' event should be present
    actions = [getattr(ev, 'kwargs', {}).get('action') for ev in tel.captured]
    assert 'start' in actions
    assert 'task_completed' in actions
    # Telemetry should have been flushed in finally
    assert tel.flushed is True

    # BrowserSession.kill should have been awaited and set killed=True
    sess = FakeBrowserSession.last
    assert sess is not None
    assert sess.killed is True


@pytest.mark.asyncio
async def test_run_prompt_mode_exception_debug_round_066():
    """Simulate an exception inside the try block and debug=True so traceback.print_exc
    branch is executed. Verify telemetry.error captured, traceback invoked, flush called,
    and SystemExit raised.
    """
    cli = importlib.import_module('browser_use.cli')

    # Provide fake logging_config again (in case previous test mutated sys.modules)
    fake_logging_mod = ModuleType('browser_use.logging_config')
    fake_logging_mod.setup_logging = lambda: None
    sys.modules['browser_use.logging_config'] = fake_logging_mod

    # Fake telemetry and event as before
    class FakeTelemetry2:
        last = None

        def __init__(self):
            FakeTelemetry2.last = self
            self.captured = []
            self.flushed = False

        def capture(self, ev):
            self.captured.append(ev)

        def flush(self):
            self.flushed = True

    class FakeEvent2:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    cli.ProductTelemetry = FakeTelemetry2
    cli.CLITelemetryEvent = FakeEvent2

    # Config and LLM present so llm is in locals() when exception occurs
    cli.load_user_config = lambda: { 'browser': {}, 'agent': {} }
    cli.update_config_with_click_args = lambda cfg, ctx: cfg

    class FakeLLM2:
        def __init__(self):
            self.model = 'boom-model'

    cli.get_llm = lambda cfg: FakeLLM2()

    # AgentSettings returns settings object
    class FakeAgentSettings2:
        @classmethod
        def model_validate(cls, data):
            class S:
                def model_dump(self):
                    return {}

            return S()

    cli.AgentSettings = FakeAgentSettings2

    # BrowserProfile / BrowserSession: ensure kill would be available but should NOT be called on exception
    class FakeProfile2:
        pass

    cli.BrowserProfile = lambda user_data_dir, **kwargs: FakeProfile2()

    class FakeBrowserSession2:
        last = None

        def __init__(self, browser_profile=None):
            FakeBrowserSession2.last = self
            self.killed = False

        async def kill(self):
            self.killed = True

    cli.BrowserSession = FakeBrowserSession2

    # Agent that raises during run
    class FailingAgent:
        def __init__(self, task, llm, browser_session, source, **kwargs):
            pass

        async def run(self):
            raise RuntimeError('simulated failure')

    cli.Agent = FailingAgent

    # Replace traceback module with fake to observe print_exc call
    fake_traceback = ModuleType('traceback')
    tb_called = {'print_exc': False}

    def fake_print_exc():
        tb_called['print_exc'] = True

    fake_traceback.print_exc = fake_print_exc
    sys.modules['traceback'] = fake_traceback

    # Prevent cancellation of real test tasks and make sleep no-op
    async def fake_sleep2(duration):
        return None

    cli.asyncio.sleep = fake_sleep2
    cli.asyncio.all_tasks = lambda: set()

    # Ensure USER_DATA_DIR exists
    cli.USER_DATA_DIR = Path('/tmp')

    # Run and expect SystemExit due to sys.exit(1) in exception handling
    with pytest.raises(SystemExit):
        await cli.run_prompt_mode('will fail', ctx=object(), debug=True)

    # Telemetry should have captured an 'error' action
    tel = FakeTelemetry2.last
    assert tel is not None
    actions = [getattr(ev, 'kwargs', {}).get('action') for ev in tel.captured]
    assert 'error' in actions

    # Traceback.print_exc should have been called due to debug=True
    assert tb_called['print_exc'] is True

    # Telemetry flushed in finally
    assert tel.flushed is True

    # BrowserSession.kill should NOT have been called because failure occurred before that step
    sess = FakeBrowserSession2.last
    if sess is not None:
        assert sess.killed is False
