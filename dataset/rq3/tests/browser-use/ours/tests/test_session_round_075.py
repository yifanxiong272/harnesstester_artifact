import asyncio
import types
import pytest

import browser_use.browser.session as session_mod
from browser_use.browser.session import BrowserSession


class DummyLogger:
    def __init__(self):
        self.debug_messages = []

    def debug(self, msg):
        # store string for later assertions
        self.debug_messages.append(str(msg))


class FakeFetchSend:
    def __init__(self, record, raise_on=None):
        # record: dict to append call info
        self._record = record
        # raise_on: set of method names that should raise when called
        self._raise_on = raise_on or set()

    async def enable(self, params=None, session_id=None):
        self._record.setdefault('enable', []).append({'params': params, 'session_id': session_id})
        if 'enable' in self._raise_on:
            raise RuntimeError('enable-failed')

    async def continueWithAuth(self, params=None, session_id=None):
        self._record.setdefault('continueWithAuth', []).append({'params': params, 'session_id': session_id})
        if 'continueWithAuth' in self._raise_on:
            raise RuntimeError('continueWithAuth-failed')

    async def continueRequest(self, params=None, session_id=None):
        self._record.setdefault('continueRequest', []).append({'params': params, 'session_id': session_id})
        if 'continueRequest' in self._raise_on:
            raise RuntimeError('continueRequest-failed')


class FakeRegisterFetch:
    def __init__(self):
        self.handlers = {}

    def authRequired(self, handler):
        # store the handler under a known key
        self.handlers['authRequired'] = handler

    def requestPaused(self, handler):
        self.handlers['requestPaused'] = handler


class FakeRootClient:
    def __init__(self, send_record, raise_on=None):
        self.send = types.SimpleNamespace(Fetch=FakeFetchSend(send_record, raise_on))
        self.register = types.SimpleNamespace(Fetch=FakeRegisterFetch())


class DummyProxy:
    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password


class DummyBrowserProfile:
    def __init__(self, proxy):
        self.proxy = proxy


@pytest.mark.asyncio
async def test_no_credentials_round_075(monkeypatch):
    """If proxy credentials are missing, setup should log and return early."""
    # Prepare a dummy self with minimal attributes required by the method
    dummy = types.SimpleNamespace()
    dummy._cdp_client_root = object()  # only used for truthiness in assert
    dummy.browser_profile = DummyBrowserProfile(proxy=DummyProxy(username=None, password=None))
    dummy.agent_focus_target_id = None
    logger = DummyLogger()
    dummy.logger = logger

    # Bind the unbound function to our dummy instance and call
    bound = types.MethodType(session_mod.BrowserSession._setup_proxy_auth, dummy)

    # Call and ensure it returns without enabling Fetch
    await bound()

    # Assert expected debug message returned early
    assert any('Proxy credentials not provided' in m for m in logger.debug_messages), (
        'expected debug message about missing proxy credentials')


@pytest.mark.asyncio
async def test_setup_proxy_auth_handlers_round_075(monkeypatch):
    """Comprehensive flow: enable on root, register handlers, and exercise auth and request handlers.

    This test patches create_task_with_error_handling to schedule tasks and awaits them deterministically.
    """
    # Recording structures
    root_send_record = {}
    focused_send_record = {}

    # Setup fake root client where enable will succeed
    fake_root = FakeRootClient(root_send_record)

    # Setup a focused cdp session (for when agent_focus_target_id is set)
    fake_focused = types.SimpleNamespace()
    fake_focused.session_id = 'sess-1'
    fake_focused.cdp_client = types.SimpleNamespace(send=types.SimpleNamespace(Fetch=FakeFetchSend(focused_send_record)))
    fake_focused.cdp_client.register = types.SimpleNamespace(Fetch=FakeRegisterFetch())

    # Create dummy self
    dummy = types.SimpleNamespace()
    dummy._cdp_client_root = fake_root
    # Provide credentials to trigger auth flow
    dummy.browser_profile = DummyBrowserProfile(proxy=DummyProxy(username='u', password='p'))
    dummy.agent_focus_target_id = None  # start without focused target
    logger = DummyLogger()
    dummy.logger = logger

    # Provide get_or_create_cdp_session that returns our fake focused session when called
    async def get_or_create_cdp_session(target_id, focus=False):
        return fake_focused

    dummy.get_or_create_cdp_session = get_or_create_cdp_session

    # Monkeypatch create_task_with_error_handling to schedule tasks and keep list
    scheduled = []

    def fake_create_task_with_error_handling(coro, name=None, logger_instance=None, suppress_exceptions=False):
        # schedule the coroutine and keep reference so test can await
        task = asyncio.create_task(coro)
        scheduled.append(task)
        return task

    monkeypatch.setattr(session_mod, 'create_task_with_error_handling', fake_create_task_with_error_handling)

    # Bind and run _setup_proxy_auth
    bound = types.MethodType(session_mod.BrowserSession._setup_proxy_auth, dummy)
    await bound()

    # After setup, root.register should have handlers
    auth_handler = fake_root.register.Fetch.handlers.get('authRequired')
    paused_handler = fake_root.register.Fetch.handlers.get('requestPaused')
    assert auth_handler is not None, 'authRequired handler must be registered on root'
    assert paused_handler is not None, 'requestPaused handler must be registered on root'

    # 1) Call auth handler with missing requestId -> should return quickly and not schedule
    auth_handler({})
    # ensure nothing scheduled by that call
    await asyncio.sleep(0)  # allow any microtasks (there should be none)
    assert len(scheduled) == 0

    # 2) Call auth handler with proxy challenge and requestId -> should schedule _respond that triggers continueWithAuth
    auth_event_proxy = {'requestId': 'r1', 'authChallenge': {'source': 'proxy'}}
    auth_handler(auth_event_proxy)
    # await scheduled tasks
    assert len(scheduled) == 1
    await asyncio.gather(*scheduled)

    # verify continueWithAuth call recorded on root send
    cwas = root_send_record.get('continueWithAuth')
    assert cwas and cwas[-1]['params']['requestId'] == 'r1'
    assert cwas[-1]['params']['authChallengeResponse']['username'] == 'u'
    assert cwas[-1]['params']['authChallengeResponse']['password'] == 'p'

    # clear scheduled for next checks
    scheduled.clear()

    # 3) Call auth handler with non-proxy => default branch
    auth_event_default = {'requestId': 'r2', 'authChallenge': {'source': 'server'}}
    auth_handler(auth_event_default)
    await asyncio.gather(*scheduled) if scheduled else asyncio.sleep(0)
    # check default continueWithAuth call
    cwas = root_send_record.get('continueWithAuth')
    assert any(call['params']['requestId'] == 'r2' and call['params']['authChallengeResponse']['response'] == 'Default' for call in cwas), (
        'expected Default response continueWithAuth call for non-proxy challenge')

    scheduled.clear()

    # 4) Call requestPaused handler with missing requestId -> should return and do nothing
    paused_handler({})
    await asyncio.sleep(0)

    # 5) Call requestPaused with requestId -> schedules continueRequest
    paused_handler({'requestId': 'r3'})
    assert len(scheduled) == 1
    await asyncio.gather(*scheduled)
    crr = root_send_record.get('continueRequest')
    assert crr and crr[-1]['params']['requestId'] == 'r3'

    # 6) Now exercise focused-session paths: set agent_focus_target_id and make get_or_create_cdp_session called in code paths
    dummy.agent_focus_target_id = 'target-1'

    # Replace root and focused send to simulate enable raising on focused enable to test exception handling
    focused_send_record.clear()
    fake_focused.cdp_client.send.Fetch = FakeFetchSend(focused_send_record, raise_on={'enable'})

    # Re-run _setup_proxy_auth to exercise focused-session enable exception paths and registration on focused client
    logger.debug_messages.clear()
    root_send_record.clear()
    scheduled.clear()

    bound = types.MethodType(session_mod.BrowserSession._setup_proxy_auth, dummy)
    await bound()

    # If focused enable raised, we should have recorded a debug message about it
    assert any('Fetch.enable on focused session failed' in m or 'Skipping proxy auth setup' in m or 'Fetch.enable on focused' in m for m in logger.debug_messages), (
        'expected debug about focused enable failing or skipping')
