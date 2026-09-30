import types
import builtins
import importlib
import pytest

from types import SimpleNamespace

MODULE_PATH = "openhands.runtime.impl.kubernetes.kubernetes_runtime"
CLASS_NAME = "KubernetesRuntime"


def _make_runtime_stub(module, pvc_exists=True, wait_raises=None, pod_raise=None):
    """Create a minimal KubernetesRuntime-like instance by bypassing __init__.

    - module: imported module containing KubernetesRuntime
    - pvc_exists: whether _pvc_exists() returns True
    - wait_raises: exception instance to raise from _wait_until_ready (or None)
    - pod_raise: exception instance to raise from create_namespaced_pod (or None)
    """
    KubeClass = getattr(module, CLASS_NAME)
    inst = object.__new__(KubeClass)

    # Simple log collector
    inst.logs = []

    def log(level, msg):
        inst.logs.append((level, msg))

    inst.log = log

    # record set_runtime_status calls
    inst.status_calls = []

    def set_runtime_status(st):
        inst.status_calls.append(st)

    inst.set_runtime_status = set_runtime_status

    # basic attributes used in the method
    inst.api_url = "http://test-api"
    inst.pod_name = "pod1"
    inst._k8s_namespace = "ns"

    # Provide manifest getters
    inst._get_runtime_pod_manifest = lambda: {"pod": True}
    inst._get_runtime_service_manifest = lambda: {"svc": 1}
    inst._get_vscode_service_manifest = lambda: {"vscode_svc": 2}
    inst._get_pvc_manifest = lambda: {"pvc": "manifest"}
    inst._get_vscode_ingress_manifest = lambda: {"ingress": True}

    inst._get_pvc_name = lambda pod_name: f"{pod_name}-pvc"
    inst._get_svc_name = lambda pod_name: f"{pod_name}-svc"
    inst._get_vscode_svc_name = lambda pod_name: f"{pod_name}-vscode-svc"
    inst._get_vscode_ingress_name = lambda pod_name: f"{pod_name}-ingress"

    inst._pvc_exists = lambda: pvc_exists

    # Networking client
    class FakeNetworking:
        def __init__(self):
            self.ingress_calls = []

        def create_namespaced_ingress(self, namespace, body):
            self.ingress_calls.append((namespace, body))

    inst.k8s_networking_client = FakeNetworking()

    # k8s client that records calls and optionally raises
    class FakeK8sClient:
        def __init__(self):
            self.pvc_calls = []
            self.pod_calls = []
            self.svc_calls = []

        def create_namespaced_persistent_volume_claim(self, namespace, body):
            self.pvc_calls.append((namespace, body))

        def create_namespaced_pod(self, namespace, body):
            if pod_raise is not None:
                raise pod_raise
            self.pod_calls.append((namespace, body))

        def create_namespaced_service(self, namespace, body):
            self.svc_calls.append((namespace, body))

    inst.k8s_client = FakeK8sClient()

    # _wait_until_ready behavior
    def _wait():
        if wait_raises is not None:
            raise wait_raises
        inst.wait_called = True

    inst._wait_until_ready = _wait

    return inst


def _patch_module_client_api_exc(module):
    """Replace module.client with a fake that exposes rest.ApiException class.

    This avoids dependency on the real kubernetes package.
    """
    class ApiException(Exception):
        pass

    fake_client = SimpleNamespace(rest=SimpleNamespace(ApiException=ApiException))
    setattr(module, "client", fake_client)
    return ApiException


def test_init_k8s_resources_when_pvc_exists_creates_resources_round_073(monkeypatch):
    mod = importlib.import_module(MODULE_PATH)
    ApiException = _patch_module_client_api_exc(mod)

    inst = _make_runtime_stub(mod, pvc_exists=True)

    # Execute
    inst._init_k8s_resources()

    # Assertions: pvc should NOT be created, pod and services and ingress should be
    assert getattr(inst.k8s_client, "pvc_calls") == []
    assert len(inst.k8s_client.pod_calls) == 1
    assert len(inst.k8s_client.svc_calls) == 2
    assert len(inst.k8s_networking_client.ingress_calls) == 1

    # _wait_until_ready should have been invoked
    assert getattr(inst, "wait_called", False) is True

    # Logs should contain the initial preparation and created pod messages
    messages = [m for _, m in inst.logs]
    assert any("Preparing to start pod" in m for m in messages)
    assert any(f"Created pod {inst.pod_name}." in m for m in messages)
    assert any("Created service" in m for m in messages)


def test_init_k8s_resources_when_pvc_missing_creates_pvc_and_logs_round_073(monkeypatch):
    mod = importlib.import_module(MODULE_PATH)
    ApiException = _patch_module_client_api_exc(mod)

    inst = _make_runtime_stub(mod, pvc_exists=False)

    inst._init_k8s_resources()

    # PVC should be created once with correct namespace and body
    assert len(inst.k8s_client.pvc_calls) == 1
    ns, body = inst.k8s_client.pvc_calls[0]
    assert ns == inst._k8s_namespace
    assert body == {"pvc": "manifest"}

    # Log should include message about creating PVC with pvc name
    messages = [m for _, m in inst.logs]
    pvc_name_msg = f'Created PVC {inst._get_pvc_name(inst.pod_name)}'
    assert any(pvc_name_msg in m for m in messages)


def test_init_k8s_resources_api_exception_is_logged_and_reraised_round_073(monkeypatch):
    mod = importlib.import_module(MODULE_PATH)
    ApiException = _patch_module_client_api_exc(mod)

    # Cause the pod creation to raise an ApiException
    api_exc = ApiException("api failure")
    inst = _make_runtime_stub(mod, pvc_exists=True, pod_raise=api_exc)

    with pytest.raises(ApiException) as ei:
        inst._init_k8s_resources()

    # Ensure the same exception was propagated
    assert ei.value is api_exc

    # Error log should contain the expected prefix
    messages = [m for _, m in inst.logs]
    assert any("Failed to create pod and services" in m for m in messages)


def test_init_k8s_resources_runtime_error_from_wait_is_logged_and_reraised_round_073(monkeypatch):
    mod = importlib.import_module(MODULE_PATH)
    ApiException = _patch_module_client_api_exc(mod)

    # Make waiting raise a RuntimeError (simulates port forwarding failure)
    rte = RuntimeError("port forwarding failed")
    inst = _make_runtime_stub(mod, pvc_exists=True, wait_raises=rte)

    with pytest.raises(RuntimeError) as ei:
        inst._init_k8s_resources()

    assert ei.value is rte

    messages = [m for _, m in inst.logs]
    assert any("Port forwarding failed" in m or "Port forwarding" in m or "Created ingress" in m for m in messages) or any("Failed to create" in m for m in messages)
