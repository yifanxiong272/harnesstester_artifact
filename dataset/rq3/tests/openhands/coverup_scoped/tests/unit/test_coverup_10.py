# file: openhands/runtime/impl/kubernetes/kubernetes_runtime.py:461-574
# asked: {"lines": [464, 465, 466, 467, 470, 471, 474, 475, 478, 479, 480, 481, 484, 485, 486, 487, 488, 494, 495, 498, 499, 500, 503, 504, 507, 508, 509, 510, 512, 513, 514, 515, 516, 520, 521, 522, 523, 524, 525, 529, 530, 531, 532, 533, 538, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 555, 556, 557, 558, 560, 561, 562, 564, 565, 566, 567, 568, 569, 570, 574], "branches": [[470, 471], [470, 474], [474, 475], [474, 478], [498, 499], [498, 503], [503, 504], [503, 507], [556, 557], [556, 560]]}
# gained: {"lines": [464, 465, 466, 467, 470, 471, 474, 475, 478, 479, 480, 481, 484, 485, 486, 487, 488, 494, 495, 498, 499, 500, 503, 504, 507, 508, 509, 510, 512, 513, 514, 515, 516, 520, 521, 522, 523, 524, 525, 529, 530, 531, 532, 533, 538, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 555, 556, 557, 558, 560, 561, 562, 564, 565, 566, 567, 568, 569, 570, 574], "branches": [[470, 471], [474, 475], [474, 478], [498, 499], [503, 504], [503, 507], [556, 557]]}

import importlib
from types import SimpleNamespace

import pytest


def _find_env(env_list, name):
    for e in env_list:
        if getattr(e, "name", None) == name:
            return e
    return None


def test_get_runtime_pod_manifest_creates_expected_pod(monkeypatch):
    # Import the module and class under test
    m = importlib.import_module("openhands.runtime.impl.kubernetes.kubernetes_runtime")
    KubernetesRuntime = m.KubernetesRuntime

    # Monkeypatch the external command builder to a simple predictable value
    monkeypatch.setattr(
        m,
        "get_action_execution_server_startup_command",
        lambda server_port, plugins, app_config, override_user_id, override_username: ["run-server"],
    )

    # Ensure node_selector and tolerations properties return predictable values
    monkeypatch.setattr(
        KubernetesRuntime,
        "node_selector",
        property(lambda self: {"k": "v"}),
        raising=False,
    )

    # Provide a vscode_enabled property so we can control that branch
    monkeypatch.setattr(
        KubernetesRuntime,
        "vscode_enabled",
        property(lambda self: True),
        raising=False,
    )

    # Use the kubernetes client exposed in the module for creating a toleration object
    # If kubernetes client model is available, create a toleration; otherwise use a simple object.
    try:
        toleration_obj = m.client.V1Toleration(key="key", value="val")
    except Exception:
        toleration_obj = {"key": "key", "value": "val"}

    monkeypatch.setattr(
        KubernetesRuntime,
        "tolerations",
        property(lambda self: [toleration_obj]),
        raising=False,
    )

    # Build config and k8s_config objects expected by _get_runtime_pod_manifest
    sandbox = SimpleNamespace(
        runtime_container_image="test-image",
        base_container_image=None,
        runtime_startup_env_vars={"RUNTIME_A": "1", "RUNTIME_B": "2"},
        workspace_mount_path_in_sandbox="/openhands/workspace",
    )
    k8s_config = SimpleNamespace(
        resource_memory_limit="1Gi",
        resource_cpu_request="500m",
        resource_memory_request="512Mi",
        privileged=True,
        image_pull_secret="my-secret",
        namespace="default",
    )
    # Note: the implementation expects workspace_mount_path_in_sandbox on config directly in some code paths.
    config = SimpleNamespace(
        debug=True,
        kubernetes=k8s_config,
        sandbox=sandbox,
        workspace_mount_path_in_sandbox=sandbox.workspace_mount_path_in_sandbox,
    )

    # Create an instance without calling __init__ to avoid side effects, then set required attrs
    runtime = object.__new__(KubernetesRuntime)
    runtime._container_port = 8080
    runtime._vscode_port = 8081
    runtime.config = config
    runtime._k8s_config = k8s_config
    runtime.plugins = []
    runtime.pod_image = "test-image"
    runtime.pod_name = "pod-xyz"
    runtime.sid = "session-123"
    # app ports: ensure the for-loop that appends ports executes
    runtime._app_ports = [30082, 30083]

    # Call the method under test
    pod = runtime._get_runtime_pod_manifest()

    # Assertions to verify postconditions and that branches executed
    assert pod is not None
    assert getattr(pod, "metadata", None) is not None
    assert pod.metadata.name == runtime.pod_name
    # labels present
    assert pod.metadata.labels["app"] == m.POD_LABEL
    assert pod.metadata.labels["session"] == runtime.sid

    # Spec checks
    assert pod.spec.restart_policy == "Never"
    # Node selector and tolerations should be present from the monkeypatched properties
    assert pod.spec.node_selector == {"k": "v"}
    assert pod.spec.tolerations is not None
    assert len(pod.spec.tolerations) >= 1

    # Container checks
    containers = pod.spec.containers
    assert len(containers) == 1
    container = containers[0]
    assert container.name == "runtime"
    assert container.image == runtime.pod_image
    # command replaced by our monkeypatched value
    assert container.command == ["run-server"]

    # Environment variables: port, PYTHONUNBUFFERED, VSCODE_PORT, DEBUG, and runtime startup env vars
    env = container.env
    assert _find_env(env, "port") is not None and _find_env(env, "port").value == str(runtime._container_port)
    assert _find_env(env, "PYTHONUNBUFFERED") is not None and _find_env(env, "PYTHONUNBUFFERED").value == "1"
    assert _find_env(env, "VSCODE_PORT") is not None and _find_env(env, "VSCODE_PORT").value == str(runtime._vscode_port)
    # DEBUG should be present because config.debug is True
    assert _find_env(env, "DEBUG") is not None and _find_env(env, "DEBUG").value == "true"
    # runtime startup env vars must be present
    assert _find_env(env, "RUNTIME_A") is not None and _find_env(env, "RUNTIME_A").value == "1"
    assert _find_env(env, "RUNTIME_B") is not None and _find_env(env, "RUNTIME_B").value == "2"

    # Volume mounts and volumes
    assert container.volume_mounts is not None
    assert len(container.volume_mounts) == 1
    assert container.volume_mounts[0].name == "workspace-volume"
    # mount_path may come from config.workspace_mount_path_in_sandbox (some code paths)
    assert container.volume_mounts[0].mount_path == runtime.config.workspace_mount_path_in_sandbox

    volumes = pod.spec.volumes
    assert volumes is not None
    assert len(volumes) == 1
    pvc = volumes[0].persistent_volume_claim
    # claim name should be produced via _get_pvc_name
    expected_pvc = runtime._get_pvc_name(runtime.pod_name)
    assert pvc.claim_name == expected_pvc

    # Container ports: http + vscode + app ports
    ports = container.ports
    names = {getattr(p, "name", None): getattr(p, "container_port", None) for p in ports}
    assert "http" in names and names["http"] == runtime._container_port
    assert "vscode" in names and names["vscode"] == runtime._vscode_port
    found_app_ports = [p.container_port for p in ports if p.container_port in runtime._app_ports]
    assert set(found_app_ports) == set(runtime._app_ports)

    # Readiness probe check
    assert container.readiness_probe is not None
    probe = container.readiness_probe
    assert probe.http_get.path == "/alive"
    # port may be an int or an IntOrString; compare as int if possible
    try:
        port_val = int(probe.http_get.port)
    except Exception:
        port_val = probe.http_get.port
    assert port_val == runtime._container_port

    # Resources check
    resources = container.resources
    assert resources.limits["memory"] == runtime._k8s_config.resource_memory_limit
    assert resources.requests["cpu"] == runtime._k8s_config.resource_cpu_request
    assert resources.requests["memory"] == runtime._k8s_config.resource_memory_request

    # Security context check
    assert container.security_context.privileged == runtime._k8s_config.privileged

    # Image pull secrets should be set because we provided image_pull_secret
    assert pod.spec.image_pull_secrets is not None
    assert len(pod.spec.image_pull_secrets) == 1
    assert getattr(pod.spec.image_pull_secrets[0], "name", None) == runtime._k8s_config.image_pull_secret
