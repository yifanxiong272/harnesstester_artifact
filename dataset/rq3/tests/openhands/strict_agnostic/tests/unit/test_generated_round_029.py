import asyncio
import types
import importlib
import pytest

kmod = importlib.import_module('openhands.runtime.impl.kubernetes.kubernetes_runtime')
from openhands.core.exceptions import (
    AgentRuntimeDisconnectedError,
    AgentRuntimeNotFoundError,
)
from openhands.runtime.runtime_status import RuntimeStatus


class DummySelf:
    def __init__(self):
        self.sid = 'sid-123'
        self.attach_to_existing = False
        self.api_url = 'https://k8s.example'
        self.pod_name = 'pod-1'
        self.pod_image = 'img:latest'
        self.vscode_url = 'https://vscode.example'
        self.plugins = []
        self._runtime_initialized = False

        self.logged = []
        self.status_calls = []
        self.setup_called = False

    def log(self, level, msg):
        # record logs for assertions
        self.logged.append((level, msg))

    def set_runtime_status(self, status, *args):
        # record status changes
        self.status_calls.append((status, args))


async def _fake_call_sync_from_async(func, *args, **kwargs):
    # simple wrapper that runs the provided synchronous function and returns its result
    return func(*args, **kwargs)


def make_api_exception_class():
    class FakeApiException(Exception):
        pass

    return FakeApiException


def _attach_raiser(exc):
    def fn():
        raise exc('attach failed')

    return fn


def _simple_success():
    def fn():
        return 'ok'

    return fn


# Test: attach_to_existing True and _attach_to_pod raises client.rest.ApiException -> raises AgentRuntimeDisconnectedError
def test_connect_attach_existing_api_exception_round_029(monkeypatch):
    dummy = DummySelf()
    dummy.attach_to_existing = True

    FakeApiException = make_api_exception_class()

    # patch module-level names
    monkeypatch.setattr(kmod, 'call_sync_from_async', _fake_call_sync_from_async)
    # ensure client.rest.ApiException resolves to our fake class used for raising
    fake_client = types.SimpleNamespace(rest=types.SimpleNamespace(ApiException=FakeApiException))
    monkeypatch.setattr(kmod, 'client', fake_client)

    dummy._attach_to_pod = _attach_raiser(FakeApiException)

    # call the async connect function
    with pytest.raises(AgentRuntimeDisconnectedError):
        asyncio.run(kmod.KubernetesRuntime.connect(dummy))

    # ensure initial status STARTING_RUNTIME was set
    assert any(call[0] == RuntimeStatus.STARTING_RUNTIME for call in dummy.status_calls)

    # error log about pod not found should be present when attach_to_existing is True
    assert any('not found' in str(msg).lower() or 'cannot connect' in str(msg).lower() for _, msg in dummy.logged)

    # ensure runtime not marked initialized
    assert dummy._runtime_initialized is False


# Test: attach_to_existing=False, _attach_to_pod raises ApiException, _init_k8s_resources raises -> AgentRuntimeNotFoundError
def test_connect_init_k8s_failure_round_029(monkeypatch):
    dummy = DummySelf()
    dummy.attach_to_existing = False

    FakeApiException = make_api_exception_class()
    monkeypatch.setattr(kmod, 'call_sync_from_async', _fake_call_sync_from_async)
    fake_client = types.SimpleNamespace(rest=types.SimpleNamespace(ApiException=FakeApiException))
    monkeypatch.setattr(kmod, 'client', fake_client)

    dummy._attach_to_pod = _attach_raiser(FakeApiException)

    def init_fail():
        raise RuntimeError('init fail')

    dummy._init_k8s_resources = init_fail

    with pytest.raises(AgentRuntimeNotFoundError):
        asyncio.run(kmod.KubernetesRuntime.connect(dummy))

    # ensure a log entry about failure to initialize k8s resources exists
    assert any('failed to initialize k8s resources' in str(msg).lower() for _, msg in dummy.logged)

    # runtime shouldn't be initialized
    assert dummy._runtime_initialized is False


# Test: attach_to_existing=False, init succeeds, wait_until_ready raises -> AgentRuntimeDisconnectedError and status ERROR_RUNTIME_DISCONNECTED
def test_connect_wait_until_ready_failure_round_029(monkeypatch):
    dummy = DummySelf()
    dummy.attach_to_existing = False

    FakeApiException = make_api_exception_class()
    monkeypatch.setattr(kmod, 'call_sync_from_async', _fake_call_sync_from_async)
    fake_client = types.SimpleNamespace(rest=types.SimpleNamespace(ApiException=FakeApiException))
    monkeypatch.setattr(kmod, 'client', fake_client)

    # attach raises -> go into init path
    dummy._attach_to_pod = _attach_raiser(FakeApiException)

    # init succeeds
    dummy._init_k8s_resources = _simple_success()

    # wait fails
    def wait_fail():
        raise RuntimeError('alive fail')

    dummy._wait_until_ready = wait_fail

    with pytest.raises(AgentRuntimeDisconnectedError):
        asyncio.run(kmod.KubernetesRuntime.connect(dummy))

    # ensure error log about failure to connect to runtime
    assert any('failed to connect to runtime' in str(msg).lower() for _, msg in dummy.logged)

    # ensure set_runtime_status called with ERROR_RUNTIME_DISCONNECTED at some point
    assert any(call[0] == RuntimeStatus.ERROR_RUNTIME_DISCONNECTED for call in dummy.status_calls)

    assert dummy._runtime_initialized is False


# Test: full success path: init succeeds, wait succeeds, setup_initial_env called, final status READY and _runtime_initialized True
def test_connect_success_round_029(monkeypatch):
    dummy = DummySelf()
    dummy.attach_to_existing = False

    FakeApiException = make_api_exception_class()
    monkeypatch.setattr(kmod, 'call_sync_from_async', _fake_call_sync_from_async)
    fake_client = types.SimpleNamespace(rest=types.SimpleNamespace(ApiException=FakeApiException))
    monkeypatch.setattr(kmod, 'client', fake_client)

    # attach raises to force init path
    dummy._attach_to_pod = _attach_raiser(FakeApiException)

    # init succeeds
    dummy._init_k8s_resources = _simple_success()

    # wait succeeds
    dummy._wait_until_ready = _simple_success()

    # setup_initial_env should be called via call_sync_from_async
    def setup_env():
        dummy.setup_called = True

    dummy.setup_initial_env = setup_env

    # run connect
    asyncio.run(kmod.KubernetesRuntime.connect(dummy))

    # after successful connect, runtime should be initialized and READY status set
    assert dummy._runtime_initialized is True
    assert dummy.setup_called is True
    assert any(call[0] == RuntimeStatus.READY for call in dummy.status_calls), (
        f"Expected READY in {dummy.status_calls}"
    )

    # ensure final log mentions plugins and vscode url
    assert any('vscode url' in str(msg).lower() or 'pod initialized' in str(msg).lower() for _, msg in dummy.logged)
