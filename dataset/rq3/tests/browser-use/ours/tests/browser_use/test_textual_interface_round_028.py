import asyncio
import sys
import types
from types import SimpleNamespace

import logging
import pytest

import browser_use.cli as cli

# All test functions must end with _round_028

class _RecorderLogger:
    def __init__(self):
        self.info_msgs = []
        self.debug_msgs = []
        self.error_msgs = []

    def info(self, msg, *a, **k):
        self.info_msgs.append(str(msg))

    def debug(self, msg, *a, **k):
        self.debug_msgs.append(str(msg))

    def error(self, msg, *a, **k):
        self.error_msgs.append(str(msg))


class _FakeRootLogger:
    def __init__(self):
        # pre-populate with a dummy handler to exercise removal loop
        self.handlers = [object()]
        self.removed = []
        self.added = []
        # Provide level attribute and name expected by pytest logging
        self.level = logging.WARNING
        self.name = 'root'

    # Methods used by the code under test and pytest's logging plugin
    def removeHandler(self, handler):
        # emulate real logger behavior
        try:
            self.handlers.remove(handler)
        except ValueError:
            pass
        self.removed.append(handler)

    def addHandler(self, handler):
        self.added.append(handler)
        self.handlers.append(handler)

    def setLevel(self, level):
        self.level = level

    def getEffectiveLevel(self):
        return self.level


class FakeProfile:
    def __init__(self, user_data_dir=None, **kwargs):
        # record what was passed
        self.user_data_dir = user_data_dir
        self.kwargs = kwargs


class FakeSession:
    def __init__(self, browser_profile=None, **kwargs):
        # emulate minimal BrowserSession API used in textual_interface
        self.browser_profile = browser_profile
        self.id = "session-01234"


class FakeController:
    def __init__(self):
        pass


class FakeApp:
    def __init__(self, config):
        self.config = config
        self.run_called = False
        # placeholders that textual_interface will set
        self.browser_session = None
        self.controller = None
        self.llm = None

    async def run_async(self):
        # emulate async run, mark called and return immediately
        self.run_called = True


class FakeLLM:
    def __init__(self, model_name=None, model=None, temperature=0.0):
        # attributes accessed by textual_interface
        if model_name is not None:
            self.model_name = model_name
        if model is not None:
            self.model = model
        self.temperature = temperature


@pytest.mark.parametrize("executable_path, headless, setup_pipes_raises, expect_headless_str", [
    ("/usr/bin/fake-chrome", True, False, "headless"),
    (None, False, True, "visible"),
])
def test_textual_interface_variants_round_028(monkeypatch, executable_path, headless, setup_pipes_raises, expect_headless_str):
    """Run textual_interface with controlled stubs to exercise logging branches.

    This single parametrized test covers:
    - the root logger handler-removal loop (handlers present)
    - branch where executable_path is present vs absent
    - branch where headless True vs False (visible)
    - successful setup_log_pipes vs an exception path inside its try/except
    - LLM info logging path
    """

    # Prepare a recorder for the module-level startup logger used in textual_interface
    startup_logger = _RecorderLogger()
    root_logger = _FakeRootLogger()

    def fake_getLogger(name=None):
        # textual_interface calls logging.getLogger('browser_use.startup') and
        # logging.getLogger() for the root logger inside setup_textual_logging
        if name == 'browser_use.startup':
            return startup_logger
        # any other name -> act as root logger
        return root_logger

    # Patch the logging.getLogger used by the module under test
    monkeypatch.setattr(cli.logging, 'getLogger', fake_getLogger, raising=True)

    # Patch BrowserProfile and BrowserSession to avoid real browser operations
    monkeypatch.setattr(cli, 'BrowserProfile', FakeProfile, raising=True)
    monkeypatch.setattr(cli, 'BrowserSession', FakeSession, raising=True)

    # Patch Controller and BrowserUseApp classes used in the function
    monkeypatch.setattr(cli, 'Controller', FakeController, raising=True)
    monkeypatch.setattr(cli, 'BrowserUseApp', FakeApp, raising=True)

    # Patch get_llm to return a deterministic fake LLM
    def fake_get_llm(cfg):
        # if model name provided in config, make model_name available, else model
        model_conf = (cfg or {}).get('model', {})
        if 'name' in model_conf:
            return FakeLLM(model_name=model_conf['name'], temperature=0.12)
        return FakeLLM(model='fallback-model', temperature=0.0)

    monkeypatch.setattr(cli, 'get_llm', fake_get_llm, raising=True)

    # Prepare logging_config.setup_log_pipes to either succeed or raise
    def setup_pipes_ok(session_id=None):
        # record a simple attribute on the function object to assert it was called
        setup_pipes_ok.called_with = session_id

    def setup_pipes_fail(session_id=None):
        raise RuntimeError('no fifo')

    logging_config_mod = types.SimpleNamespace(
        setup_log_pipes=(setup_pipes_fail if setup_pipes_raises else setup_pipes_ok)
    )

    # Inject a fake module for browser_use.logging_config so the dynamic import inside
    # textual_interface picks up our stub
    monkeypatch.setitem(sys.modules, 'browser_use.logging_config', logging_config_mod)

    # Build config used by textual_interface
    cfg = {
        'browser': {},
        'model': {'name': 'explicit-model'} if not setup_pipes_raises else {'name': 'explicit-model'},
    }
    if executable_path is not None:
        cfg['browser']['executable_path'] = executable_path
    # Only include headless explicitly when given (simulate either branch)
    cfg['browser']['headless'] = headless

    # Run the async function under test
    asyncio.run(cli.textual_interface(cfg))

    # Assertions:
    # 1) ensure the startup logger recorded that Browser type is logged (common)
    #    and it recorded the LLM provider/model info
    found_browser_type = any('Browser type' in s for s in startup_logger.info_msgs + startup_logger.debug_msgs)
    assert found_browser_type, f"expected Browser type logging; got {startup_logger.info_msgs} {startup_logger.debug_msgs}"

    # 2) If executable_path was set, ensure a corresponding info message was logged
    if executable_path:
        assert any(executable_path in msg for msg in startup_logger.info_msgs), (
            "executable_path was set but not logged; infos: {}".format(startup_logger.info_msgs)
        )
    else:
        # no explicit binary logged
        assert not any('Browser binary' in msg for msg in startup_logger.info_msgs)

    # 3) Headless vs visible branch observed
    assert any(expect_headless_str in msg for msg in startup_logger.info_msgs), (
        f"expected browser mode string '{expect_headless_str}' in info messages: {startup_logger.info_msgs}"
    )

    # 4) The root logger's handler removal branch should have executed (removed list mutated)
    assert len(root_logger.removed) >= 1, "expected at least one handler to be removed from root logger"
    # And a NullHandler (or some handler) should have been added
    assert len(root_logger.added) >= 1, "expected at least one handler to be added to root logger"

    # 5) If setup_log_pipes succeeded, the fake function should have been called with the session id
    if not setup_pipes_raises:
        assert getattr(setup_pipes_ok, 'called_with', None) == 'session-01234'
    else:
        # If it raised, a debug entry about failure should be present in startup_logger.debug_msgs
        assert any('Could not set up FIFO logging pipes' in m or 'Could not set up FIFO logging pipes' in m for m in startup_logger.debug_msgs), (
            f"expected debug log about failing to set up pipes; debug msgs: {startup_logger.debug_msgs}"
        )


def test_textual_interface_llm_model_fallback_round_028(monkeypatch):
    """Ensure LLM model fallback path is exercised when model_name is missing.

    textual_interface uses: model_name = getattr(llm, 'model_name', None) or getattr(llm, 'model', 'Unknown model')
    We emulate llm without model_name but with model to hit the fallback.
    """
    startup_logger = _RecorderLogger()
    root_logger = _FakeRootLogger()

    def fake_getLogger(name=None):
        if name == 'browser_use.startup':
            return startup_logger
        return root_logger

    monkeypatch.setattr(cli.logging, 'getLogger', fake_getLogger, raising=True)

    # Minimal BrowserProfile/Session/Controller/App as before
    monkeypatch.setattr(cli, 'BrowserProfile', FakeProfile, raising=True)
    monkeypatch.setattr(cli, 'BrowserSession', FakeSession, raising=True)
    monkeypatch.setattr(cli, 'Controller', FakeController, raising=True)
    monkeypatch.setattr(cli, 'BrowserUseApp', FakeApp, raising=True)

    # LLM with no model_name but with model attribute
    def fake_get_llm(cfg):
        return FakeLLM(model='fallback-model', temperature=0.33)

    monkeypatch.setattr(cli, 'get_llm', fake_get_llm, raising=True)

    # Provide a harmless logging_config module so setup_log_pipes succeeds
    def setup_pipes_ok(session_id=None):
        setup_pipes_ok.called_with = session_id

    logging_config_mod = types.SimpleNamespace(setup_log_pipes=setup_pipes_ok)
    monkeypatch.setitem(sys.modules, 'browser_use.logging_config', logging_config_mod)

    cfg = {'browser': {'headless': False}, 'model': {}}

    asyncio.run(cli.textual_interface(cfg))

    # Expect the fallback model name present in info messages because model attribute exists
    assert any('fallback-model' in m for m in startup_logger.info_msgs), (
        f"expected fallback model name in startup info messages: {startup_logger.info_msgs}"
    )
    # setup_log_pipes should have been called with our fake session id
    assert getattr(setup_pipes_ok, 'called_with', None) == 'session-01234'
