# file: openhands/runtime/impl/kubernetes/kubernetes_runtime.py:226-284
# asked: {"lines": [228, 229, 230, 231, 233, 234, 235, 237, 238, 239, 240, 242, 244, 245, 246, 247, 248, 249, 251, 252, 253, 254, 255, 257, 258, 259, 260, 261, 262, 263, 264, 266, 268, 269, 270, 272, 273, 275, 276, 278, 279, 280, 282, 283, 284], "branches": [[237, 238], [237, 244], [257, 258], [257, 260], [272, 273], [272, 275], [275, 276], [275, 278], [282, 283], [282, 284]]}
# gained: {"lines": [228, 229, 230, 231, 233, 234, 235, 237, 238, 239, 240, 242, 244, 245, 246, 247, 248, 249, 251, 252, 253, 254, 255, 257, 258, 259, 260, 261, 262, 263, 264, 266, 268, 269, 270, 272, 273, 275, 276, 278, 279, 280, 282, 283, 284], "branches": [[237, 238], [237, 244], [257, 258], [272, 273], [275, 276], [282, 283]]}

import importlib
import pytest

k8s_mod = importlib.import_module("openhands.runtime.impl.kubernetes.kubernetes_runtime")
KubernetesRuntime = k8s_mod.KubernetesRuntime
ApiException = k8s_mod.client.rest.ApiException
AgentRuntimeDisconnectedError = k8s_mod.AgentRuntimeDisconnectedError
AgentRuntimeNotFoundError = k8s_mod.AgentRuntimeNotFoundError
RuntimeStatus = k8s_mod.RuntimeStatus


class DummyPlugin:
    def __init__(self, name):
        self.name = name


class DummyKubernetesRuntime(KubernetesRuntime):
    # Minimal fake runtime that provides attributes used by connect()
    def __init__(self, sid="dummy", attach_to_existing=False, plugins=None):
        # required by connect()
        self.sid = sid
        self.attach_to_existing = attach_to_existing
        self.api_url = "http://api-url"
        self.pod_name = "pod-" + sid
        self.pod_image = "pod-image"
        self.plugins = plugins or []
        self._runtime_initialized = False

        # Ensure vscode-related property accessors in base work
        self._vscode_enabled = False
        self._vscode_port = 8081

        # bookkeeping for assertions
        self.logged = []
        self.status_history = []

        # placeholders that tests will replace or rely on
        self._attach_to_pod = lambda: None
        self._init_k8s_resources = lambda: None
        self._wait_until_ready = lambda: None
        self.setup_initial_env = lambda: None

    def log(self, level, message):
        self.logged.append((level, message))

    def set_runtime_status(self, status, message: str | None = None):
        self.status_history.append((status, message))


# helper to replace call_sync_from_async in the module so connect() can await it
async def _fake_call_sync_from_async(func, *args, **kwargs):
    return func(*args, **kwargs)


@pytest.mark.asyncio
async def test_connect_attach_to_existing_api_exception_raises_disconnected(monkeypatch):
    monkeypatch.setattr(k8s_mod, "call_sync_from_async", _fake_call_sync_from_async)

    rt = DummyKubernetesRuntime(sid="s1", attach_to_existing=True)

    def raise_api_exc():
        raise ApiException("cannot attach")

    rt._attach_to_pod = raise_api_exc

    with pytest.raises(AgentRuntimeDisconnectedError):
        await rt.connect()

    assert any(status == RuntimeStatus.STARTING_RUNTIME for status, _ in rt.status_history)
    assert any("not found or cannot connect to it" in msg or rt.pod_name in msg for _, msg in rt.logged)


@pytest.mark.asyncio
async def test_connect_init_k8s_resources_failure_raises_notfound(monkeypatch):
    monkeypatch.setattr(k8s_mod, "call_sync_from_async", _fake_call_sync_from_async)

    rt = DummyKubernetesRuntime(sid="s2", attach_to_existing=False)

    def raise_api_exc():
        raise ApiException("attach missing")

    rt._attach_to_pod = raise_api_exc

    def init_raise():
        raise RuntimeError("init failed")

    rt._init_k8s_resources = init_raise

    with pytest.raises(AgentRuntimeNotFoundError) as excinfo:
        await rt.connect()

    assert "init failed" in str(excinfo.value)
    assert any("Failed to initialize k8s resources" in msg or "Failed to initialize kubernetes resources" in msg for _, msg in rt.logged)
    assert any(status == RuntimeStatus.STARTING_RUNTIME for status, _ in rt.status_history)


@pytest.mark.asyncio
async def test_connect_wait_until_ready_failure_raises_disconnected_and_sets_error_status(monkeypatch):
    monkeypatch.setattr(k8s_mod, "call_sync_from_async", _fake_call_sync_from_async)

    rt = DummyKubernetesRuntime(sid="s3", attach_to_existing=False)

    def raise_api_exc():
        raise ApiException("attach not present")

    rt._attach_to_pod = raise_api_exc

    rt._init_k8s_resources = lambda: None

    def wait_raise():
        raise RuntimeError("pod never ready")

    rt._wait_until_ready = wait_raise

    with pytest.raises(AgentRuntimeDisconnectedError) as excinfo:
        await rt.connect()

    assert "pod never ready" in str(excinfo.value) or "Failed to connect to runtime" in str(excinfo.value)
    assert any(status == RuntimeStatus.ERROR_RUNTIME_DISCONNECTED for status, _ in rt.status_history)
    assert any("Failed to connect to runtime" in msg for _, msg in rt.logged)


@pytest.mark.asyncio
async def test_connect_success_sets_ready_and_initializes_env(monkeypatch):
    monkeypatch.setattr(k8s_mod, "call_sync_from_async", _fake_call_sync_from_async)

    plugins = [DummyPlugin("p1"), DummyPlugin("p2")]
    rt = DummyKubernetesRuntime(sid="s4", attach_to_existing=False, plugins=plugins)

    def raise_api_exc():
        raise ApiException("attach missing")

    rt._attach_to_pod = raise_api_exc
    rt._init_k8s_resources = lambda: None
    rt._wait_until_ready = lambda: None

    flag = {"setup_called": False}

    def setup_env():
        flag["setup_called"] = True

    rt.setup_initial_env = setup_env

    await rt.connect()

    assert flag["setup_called"] is True
    assert any(status == RuntimeStatus.READY for status, _ in rt.status_history)
    assert any("Pod initialized with plugins" in msg for _, msg in rt.logged)
    assert rt._runtime_initialized is True
