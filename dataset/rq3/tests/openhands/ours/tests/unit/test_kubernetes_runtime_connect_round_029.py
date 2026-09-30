import types
import pytest

from openhands.runtime.impl.kubernetes import kubernetes_runtime as kr_mod


class LogCapture:
    def __init__(self):
        self.records = []

    def __call__(self, level, message):
        self.records.append((level, message))


class StatusCapture:
    def __init__(self):
        self.calls = []

    def __call__(self, status, message=None):
        self.calls.append((status, message))


@pytest.mark.asyncio
async def test_attach_existing_api_exception_raises_disconnected_round_029(monkeypatch):
    # Prepare a fake ApiException class and ensure module resolves it
    class FakeApiExc(Exception):
        pass

    # Patch client.rest.ApiException in the module under test
    monkeypatch.setattr(kr_mod.client, "rest", types.SimpleNamespace(ApiException=FakeApiExc), raising=False)

    # Fake call_sync_from_async that simply calls the provided sync function and lets exceptions bubble
    async def fake_call_sync_from_async(fn):
        return fn()

    monkeypatch.setattr(kr_mod, "call_sync_from_async", fake_call_sync_from_async)

    # Create instance without running __init__ and set necessary attributes
    inst = object.__new__(kr_mod.KubernetesRuntime)
    inst.sid = "sid-attach-existing"
    inst.attach_to_existing = True
    inst.api_url = "http://api"
    inst.pod_name = "pod-x"
    inst.pod_image = "img"
    inst.plugins = [types.SimpleNamespace(name="p")]
    inst._runtime_initialized = False

    # Capture logs and status changes
    log = LogCapture()
    inst.log = log
    status = StatusCapture()
    inst.set_runtime_status = status

    # _attach_to_pod will raise the ApiException to hit the branch
    def raise_api_exc():
        raise FakeApiExc("not found")

    inst._attach_to_pod = raise_api_exc

    # Call connect and assert AgentRuntimeDisconnectedError is raised and error logged
    with pytest.raises(kr_mod.AgentRuntimeDisconnectedError):
        await kr_mod.KubernetesRuntime.connect(inst)

    # Ensure an error log about the pod was emitted
    assert any(
        rec for rec in log.records if rec[0] == "error" and "Pod pod-x not found or cannot connect to it." in rec[1]
    )

    # Ensure runtime was marked as STARTING_RUNTIME at least once
    assert any(call[0] == kr_mod.RuntimeStatus.STARTING_RUNTIME for call in status.calls)


@pytest.mark.asyncio
async def test_attach_new_init_failure_raises_not_found_round_029(monkeypatch):
    # Simulate ApiException type
    class FakeApiExc(Exception):
        pass

    monkeypatch.setattr(kr_mod.client, "rest", types.SimpleNamespace(ApiException=FakeApiExc), raising=False)

    async def fake_call_sync_from_async(fn):
        return fn()

    monkeypatch.setattr(kr_mod, "call_sync_from_async", fake_call_sync_from_async)

    inst = object.__new__(kr_mod.KubernetesRuntime)
    inst.sid = "sid-new-init-fail"
    inst.attach_to_existing = False
    inst.api_url = "http://api"
    inst.pod_name = "pod-new"
    inst.pod_image = "img"
    inst.plugins = [types.SimpleNamespace(name="p1")]
    inst._runtime_initialized = False

    log = LogCapture()
    inst.log = log
    status = StatusCapture()
    inst.set_runtime_status = status

    # _attach_to_pod will raise ApiException to trigger init path
    def raise_api_exc():
        raise FakeApiExc("not found")

    # _init_k8s_resources will raise a generic error to trigger AgentRuntimeNotFoundError
    def init_fail():
        raise RuntimeError("init failed")

    inst._attach_to_pod = raise_api_exc
    inst._init_k8s_resources = init_fail

    with pytest.raises(kr_mod.AgentRuntimeNotFoundError) as excinfo:
        await kr_mod.KubernetesRuntime.connect(inst)

    # Assert the original init message is embedded in the raised exception's message
    assert "init failed" in str(excinfo.value)

    # Ensure an error log about initializing k8s resources was emitted
    assert any("Failed to initialize k8s resources" in rec[1] for rec in log.records if rec[0] == "error")


@pytest.mark.asyncio
async def test_attach_new_success_sets_ready_round_029(monkeypatch):
    # Ensure call_sync_from_async simply invokes the callable
    async def fake_call_sync_from_async(fn):
        return fn()

    monkeypatch.setattr(kr_mod, "call_sync_from_async", fake_call_sync_from_async)

    inst = object.__new__(kr_mod.KubernetesRuntime)
    inst.sid = "sid-new-success"
    inst.attach_to_existing = False
    inst.api_url = "http://api"
    inst.pod_name = "pod-ok"
    inst.pod_image = "img"
    inst.plugins = [types.SimpleNamespace(name="pluginA"), types.SimpleNamespace(name="pluginB")]
    inst._runtime_initialized = False

    log = LogCapture()
    inst.log = log
    status = StatusCapture()
    inst.set_runtime_status = status

    # _attach_to_pod succeeds (no exception)
    def attach_ok():
        return None

    # _wait_until_ready succeeds
    def wait_ok():
        return None

    # setup_initial_env will set a flag we can assert to ensure it was called
    env_setup_called = {"called": False}

    def setup_env():
        env_setup_called["called"] = True
        return None

    inst._attach_to_pod = attach_ok
    inst._wait_until_ready = wait_ok
    inst.setup_initial_env = setup_env

    # Run connect and ensure no exception
    await kr_mod.KubernetesRuntime.connect(inst)

    # After successful connect, setup_initial_env should have been invoked
    assert env_setup_called["called"] is True

    # The final runtime status should include READY
    assert any(call[0] == kr_mod.RuntimeStatus.READY for call in status.calls)

    # _runtime_initialized should be set to True at the end
    assert inst._runtime_initialized is True

    # Log should include plugin names and VSCode URL (vscode_url may be None but plugin names string should appear)
    assert any("Pod initialized with plugins" in rec[1] for rec in log.records if rec[0] == "info")
