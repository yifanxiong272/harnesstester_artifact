import importlib
import types
import pytest

# Load the module under test
kmod = importlib.import_module("openhands.runtime.impl.kubernetes.kubernetes_runtime")

# A tiny flexible fake model to stand in for kubernetes model classes
class FakeModel:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        # expose kwargs as attributes for easy assertions
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return f"FakeModel(args={self.args}, kwargs={self.kwargs})"


class FakeClient:
    V1Probe = FakeModel
    V1HTTPGetAction = FakeModel
    V1LocalObjectReference = FakeModel


@pytest.fixture(autouse=True)
def patch_k8s_models(monkeypatch):
    """Replace kubernetes models and client with light-weight fakes to avoid importing real kubernetes package
    and to make returned objects easy to inspect deterministically.
    """
    names = [
        "V1EnvVar",
        "V1VolumeMount",
        "V1Volume",
        "V1PersistentVolumeClaimVolumeSource",
        "V1ContainerPort",
        "V1ResourceRequirements",
        "V1SecurityContext",
        "V1Container",
        "V1ObjectMeta",
        "V1Pod",
        "V1PodSpec",
    ]
    for n in names:
        monkeypatch.setattr(kmod, n, FakeModel, raising=False)

    # Patch the client namespace used inside the module
    monkeypatch.setattr(kmod, "client", FakeClient(), raising=False)

    # Patch the startup command builder to a deterministic simple list
    monkeypatch.setattr(kmod, "get_action_execution_server_startup_command", lambda **kwargs: ["/fake-server", f"--port={kwargs.get('server_port')}"])

    yield


def make_runtime_like(**overrides):
    """Create a minimal object with the attributes the method uses.
    We use a SimpleNamespace-like object to act as self for the unbound method call.
    """
    ns = types.SimpleNamespace()

    # sensible defaults
    ns._container_port = overrides.get("_container_port", 8080)
    ns._vscode_port = overrides.get("_vscode_port", 3456)
    ns.plugins = overrides.get("plugins", [])
    ns.pod_image = overrides.get("pod_image", "gcr.io/fake/image:latest")
    ns.pod_name = overrides.get("pod_name", "pod-abc")
    ns.sid = overrides.get("sid", "session-1")
    ns._app_ports = overrides.get("_app_ports", [])
    ns.vscode_enabled = overrides.get("vscode_enabled", False)
    ns.node_selector = overrides.get("node_selector", None)
    ns.tolerations = overrides.get("tolerations", None)

    # k8s config
    k8s_cfg = types.SimpleNamespace(
        resource_memory_limit=overrides.get("resource_memory_limit", "512Mi"),
        resource_cpu_request=overrides.get("resource_cpu_request", "100m"),
        resource_memory_request=overrides.get("resource_memory_request", "256Mi"),
        privileged=overrides.get("privileged", False),
        image_pull_secret=overrides.get("image_pull_secret", None),
    )
    ns._k8s_config = k8s_cfg

    # config and sandbox
    sandbox = types.SimpleNamespace(runtime_startup_env_vars=overrides.get("runtime_startup_env_vars", {}),)
    cfg = types.SimpleNamespace(
        debug=overrides.get("debug", False),
        sandbox=sandbox,
        workspace_mount_path_in_sandbox=overrides.get("workspace_mount_path_in_sandbox", "/openhands/workspace"),
    )
    ns.config = cfg

    # Provide the _get_pvc_name method used in the pod manifest
    def _get_pvc_name(pod_name):
        return overrides.get("pvc_name", f"pvc-for-{pod_name}")

    ns._get_pvc_name = _get_pvc_name

    return ns


def extract_env_names(env_list):
    # env_list are FakeModel instances for V1EnvVar; they expose attributes set from kwargs
    return [(getattr(e, "name", None), getattr(e, "value", None)) for e in env_list]


def extract_ports(port_list):
    return [(getattr(p, "container_port", None), getattr(p, "name", None)) for p in port_list]


def test_debug_and_runtime_envs_and_vscode_and_app_ports_and_image_pull_secret_round_053():
    # config.debug True -> DEBUG env var should be added
    # runtime_startup_env_vars contains entries -> they should be appended
    # vscode_enabled True -> vscode port appended
    # _app_ports non-empty -> those ports appended
    # image_pull_secret set -> pod.spec.image_pull_secrets should be a list with one reference

    rt = make_runtime_like(
        _container_port=1111,
        _vscode_port=2222,
        debug=True,
        runtime_startup_env_vars={"CUSTOM": "value1", "ANOTHER": "value2"},
        vscode_enabled=True,
        _app_ports=[3000, 4000],
        image_pull_secret="my-secret",
        pvc_name="claim-xyz",
    )

    pod = kmod.KubernetesRuntime._get_runtime_pod_manifest(rt)

    # Inspect container built inside the pod
    assert hasattr(pod, "spec") and pod.spec is not None
    containers = getattr(pod.spec, "containers", None)
    assert isinstance(containers, list) and len(containers) == 1
    container = containers[0]

    # Environment contains default entries, DEBUG and the runtime startup ones
    env = getattr(container, "env", [])
    names_vals = extract_env_names(env)
    # required defaults
    assert ("port", str(rt._container_port)) in names_vals
    assert ("PYTHONUNBUFFERED", "1") in names_vals
    assert ("VSCODE_PORT", str(rt._vscode_port)) in names_vals
    # debug flag
    assert ("DEBUG", "true") in names_vals
    # runtime startup env vars
    assert ("CUSTOM", "value1") in names_vals
    assert ("ANOTHER", "value2") in names_vals

    # Ports includes http, vscode, and app ports
    ports = getattr(container, "ports", [])
    port_tuples = extract_ports(ports)
    assert (rt._container_port, "http") in port_tuples
    assert (rt._vscode_port, "vscode") in port_tuples
    assert (3000, None) in port_tuples
    assert (4000, None) in port_tuples

    # image_pull_secrets should be a list with one fake local object reference containing the secret name
    ips = getattr(pod.spec, "image_pull_secrets", None)
    assert isinstance(ips, list)
    assert len(ips) == 1
    assert getattr(ips[0], "name", None) == "my-secret"

    # pod metadata name set
    assert getattr(pod, "metadata", None) is not None
    assert getattr(pod.metadata, "name", None) == rt.pod_name


def test_no_debug_no_runtime_envs_no_vscode_no_app_ports_no_image_secret_round_053(monkeypatch):
    # Ensure module-level DEBUG is False so only config.debug controls the branch
    monkeypatch.setattr(kmod, "DEBUG", False, raising=False)

    rt = make_runtime_like(
        _container_port=5555,
        _vscode_port=6666,
        debug=False,
        runtime_startup_env_vars={},
        vscode_enabled=False,
        _app_ports=[],
        image_pull_secret=None,
        pvc_name="claim-empty",
    )

    pod = kmod.KubernetesRuntime._get_runtime_pod_manifest(rt)

    # Inspect container
    container = pod.spec.containers[0]
    env = getattr(container, "env", [])
    names_vals = extract_env_names(env)

    # Default envs present
    assert ("port", str(rt._container_port)) in names_vals
    assert ("PYTHONUNBUFFERED", "1") in names_vals
    assert ("VSCODE_PORT", str(rt._vscode_port)) in names_vals

    # DEBUG should NOT be present
    assert all(name != "DEBUG" for name, _ in names_vals)

    # No runtime startup envs were added
    assert not any(name in ("CUSTOM", "ANOTHER") for name, _ in names_vals)

    # Ports: only http present
    ports = getattr(container, "ports", [])
    port_tuples = extract_ports(ports)
    assert (rt._container_port, "http") in port_tuples
    # No vscode port
    assert not any(n == "vscode" for _, n in port_tuples)

    # image_pull_secrets should be None when not provided
    assert getattr(pod.spec, "image_pull_secrets", None) is None
