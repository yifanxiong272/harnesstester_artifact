import types
import pytest
from types import SimpleNamespace

from openhands.runtime.impl.kubernetes import kubernetes_runtime as kr_mod
from openhands.runtime.impl.kubernetes.kubernetes_runtime import KubernetesRuntime


class DummyApiException(Exception):
    pass


def _make_runtime_instance(monkeypatch):
    """Create a KubernetesRuntime-like instance with patched dependencies and simple log collection."""
    # Ensure the module-level client.rest.ApiException used by the code is our DummyApiException
    monkeypatch.setattr(kr_mod, "client", SimpleNamespace(rest=SimpleNamespace(ApiException=DummyApiException)))

    inst = object.__new__(KubernetesRuntime)

    # Simple log collector
    inst.logged = []

    def log(level, msg):
        inst.logged.append((level, msg))

    inst.log = log

    # record runtime status
    inst.runtime_status = None

    def set_runtime_status(status):
        inst.runtime_status = status

    inst.set_runtime_status = set_runtime_status

    # basic attributes used in formatting
    inst.api_url = "https://example.runtime"
    inst.pod_name = "pod-123"
    inst._k8s_namespace = "default"

    # helper name getters used in logs
    inst._get_pvc_name = lambda pod_name: f"pvc-{pod_name}"
    inst._get_svc_name = lambda pod_name: f"svc-{pod_name}"
    inst._get_vscode_svc_name = lambda pod_name: f"vscode-svc-{pod_name}"
    inst._get_vscode_ingress_name = lambda pod_name: f"vscode-ing-{pod_name}"

    # simple manifest factories
    inst._get_runtime_pod_manifest = lambda: {"kind": "Pod", "metadata": {"name": inst.pod_name}}
    inst._get_runtime_service_manifest = lambda: {"kind": "Service", "metadata": {"name": inst._get_svc_name(inst.pod_name)}}
    inst._get_vscode_service_manifest = lambda: {"kind": "Service", "metadata": {"name": inst._get_vscode_svc_name(inst.pod_name)}}
    inst._get_pvc_manifest = lambda: {"kind": "PVC", "metadata": {"name": inst._get_pvc_name(inst.pod_name)}}
    inst._get_vscode_ingress_manifest = lambda: {"kind": "Ingress", "metadata": {"name": inst._get_vscode_ingress_name(inst.pod_name)}}

    return inst


def test_init_k8s_resources_creates_pvc_and_other_resources_round_073(monkeypatch):
    """When PVC does not exist, PVC creation should be called and pod/service/ingress created, and logs reflect that."""
    inst = _make_runtime_instance(monkeypatch)

    calls = []

    # Simulate _pvc_exists -> False so PVC is created
    inst._pvc_exists = lambda: False

    # Prepare a k8s_client that records calls
    def create_pvc(namespace, body):
        calls.append(("create_pvc", namespace, body))

    def create_pod(namespace, body):
        calls.append(("create_pod", namespace, body))

    def create_service(namespace, body):
        calls.append(("create_service", namespace, body))

    k8s_client = SimpleNamespace(
        create_namespaced_persistent_volume_claim=create_pvc,
        create_namespaced_pod=create_pod,
        create_namespaced_service=create_service,
    )

    # networking client
    def create_ingress(namespace, body):
        calls.append(("create_ingress", namespace, body))

    k8s_networking_client = SimpleNamespace(create_namespaced_ingress=create_ingress)

    inst.k8s_client = k8s_client
    inst.k8s_networking_client = k8s_networking_client

    # wait until ready should be a no-op for this test
    inst._wait_until_ready = lambda: None

    # Run the method under test
    inst._init_k8s_resources()

    # Assertions about calls order and presence
    assert calls[0][0] == "create_pvc", "PVC should be created when it does not exist"
    assert calls[1][0] == "create_pod", "Pod should be created after PVC"
    assert any(c[0] == "create_service" for c in calls), "Service creation should be invoked"
    assert any(c[0] == "create_ingress" for c in calls), "Ingress creation should be invoked"

    # Check that logs include the Created PVC and Created pod messages
    joined_logs = "\n".join(f"{lvl}:{msg}" for lvl, msg in inst.logged)
    assert "Created PVC pvc-pod-123" in joined_logs
    assert "Created pod pod-123." in joined_logs


def test_init_k8s_resources_skips_pvc_when_exists_round_073(monkeypatch):
    """When PVC exists, PVC creation should be skipped but pod/service/ingress still created."""
    inst = _make_runtime_instance(monkeypatch)

    calls = []

    # Simulate _pvc_exists -> True so PVC creation is skipped
    inst._pvc_exists = lambda: True

    def create_pvc(namespace, body):
        calls.append(("create_pvc", namespace, body))

    def create_pod(namespace, body):
        calls.append(("create_pod", namespace, body))

    def create_service(namespace, body):
        calls.append(("create_service", namespace, body))

    k8s_client = SimpleNamespace(
        create_namespaced_persistent_volume_claim=create_pvc,
        create_namespaced_pod=create_pod,
        create_namespaced_service=create_service,
    )

    def create_ingress(namespace, body):
        calls.append(("create_ingress", namespace, body))

    k8s_networking_client = SimpleNamespace(create_namespaced_ingress=create_ingress)

    inst.k8s_client = k8s_client
    inst.k8s_networking_client = k8s_networking_client

    inst._wait_until_ready = lambda: None

    inst._init_k8s_resources()

    # Ensure PVC creation was not called
    assert not any(c[0] == "create_pvc" for c in calls)
    # But pod/service/ingress creation should have been called
    assert any(c[0] == "create_pod" for c in calls)
    assert any(c[0] == "create_service" for c in calls)
    assert any(c[0] == "create_ingress" for c in calls)

    joined_logs = "\n".join(f"{lvl}:{msg}" for lvl, msg in inst.logged)
    assert "Created pod pod-123." in joined_logs


def test_init_k8s_resources_api_exception_is_logged_and_reraised_round_073(monkeypatch):
    """If k8s client raises client.rest.ApiException, it should be logged as error and re-raised."""
    inst = _make_runtime_instance(monkeypatch)

    inst._pvc_exists = lambda: True

    # make create_namespaced_pod raise the ApiException type used by the module
    def create_pod(namespace, body):
        raise DummyApiException("k8s failure")

    # other methods should be no-ops
    k8s_client = SimpleNamespace(
        create_namespaced_persistent_volume_claim=lambda *a, **k: None,
        create_namespaced_pod=create_pod,
        create_namespaced_service=lambda *a, **k: None,
    )

    inst.k8s_client = k8s_client
    inst.k8s_networking_client = SimpleNamespace(create_namespaced_ingress=lambda *a, **k: None)

    inst._wait_until_ready = lambda: None

    with pytest.raises(DummyApiException):
        inst._init_k8s_resources()

    # The error log should contain the failure message prefix
    assert any(
        level == "error" and "Failed to create pod and services" in msg
        for level, msg in inst.logged
    )


def test_init_k8s_resources_wait_raises_runtime_error_round_073(monkeypatch):
    """If _wait_until_ready raises RuntimeError, it should be logged as error and re-raised."""
    inst = _make_runtime_instance(monkeypatch)

    inst._pvc_exists = lambda: True

    # normal creation methods
    k8s_client = SimpleNamespace(
        create_namespaced_persistent_volume_claim=lambda *a, **k: None,
        create_namespaced_pod=lambda *a, **k: None,
        create_namespaced_service=lambda *a, **k: None,
    )
    inst.k8s_client = k8s_client
    inst.k8s_networking_client = SimpleNamespace(create_namespaced_ingress=lambda *a, **k: None)

    # make wait raise
    inst._wait_until_ready = lambda: (_ for _ in ()).throw(RuntimeError("port forward failure"))

    with pytest.raises(RuntimeError):
        inst._init_k8s_resources()

    assert any(level == "error" and "Port forwarding failed" in msg for level, msg in inst.logged)
