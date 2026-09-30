# file: openhands/runtime/impl/kubernetes/kubernetes_runtime.py:88-158
# asked: {"lines": [102, 103, 104, 105, 106, 107, 110, 111, 112, 115, 116, 117, 121, 122, 123, 126, 127, 128, 129, 130, 133, 135, 136, 138, 140, 143, 144, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157], "branches": [[102, 103], [102, 110], [115, 116], [115, 121], [136, 138], [136, 140]]}
# gained: {"lines": [102, 103, 104, 105, 106, 107, 110, 111, 112, 115, 116, 117, 121, 122, 123, 126, 127, 128, 129, 130, 133, 135, 136, 138, 140, 143, 144, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157], "branches": [[102, 103], [115, 116], [115, 121], [136, 138]]}

import importlib
import types
import uuid

import pytest


MODULE_PATH = "openhands.runtime.impl.kubernetes.kubernetes_runtime"


@pytest.fixture(autouse=True)
def reset_kubernetes_runtime_class_state():
    """
    Ensure class-level state is reset between tests.
    """
    mod = importlib.import_module(MODULE_PATH)
    # Save originals to restore after tests
    orig_shutdown = getattr(mod, "add_shutdown_listener", None)
    orig_action_client_init = getattr(mod.ActionExecutionClient, "__init__", None) if getattr(mod, "ActionExecutionClient", None) else None
    orig_init_k8s = getattr(mod.KubernetesRuntime, "_init_kubernetes_client", None)
    try:
        # Reset class-level attrs
        mod.KubernetesRuntime._shutdown_listener_id = None
        mod.KubernetesRuntime._namespace = ""
        yield
    finally:
        # restore originals if present
        if orig_shutdown is not None:
            setattr(mod, "add_shutdown_listener", orig_shutdown)
        if orig_action_client_init is not None and getattr(mod, "ActionExecutionClient", None):
            setattr(mod.ActionExecutionClient, "__init__", orig_action_client_init)
        if orig_init_k8s is not None:
            setattr(mod.KubernetesRuntime, "_init_kubernetes_client", orig_init_k8s)
        # Ensure class vars cleared
        mod.KubernetesRuntime._shutdown_listener_id = None
        mod.KubernetesRuntime._namespace = ""


def make_minimal_config(k8s_namespace: str | None):
    """
    Return a minimal object mimicking OpenHandsConfig used by KubernetesRuntime.
    """
    class KubeCfg:
        def __init__(self, namespace):
            self.namespace = namespace

    class Sandbox:
        def __init__(self, runtime_container_image=None, base_container_image=None):
            self.runtime_container_image = runtime_container_image
            self.base_container_image = base_container_image

    class Cfg:
        def __init__(self, kubernetes, runtime_img=None, base_img=None):
            self.kubernetes = KubeCfg(kubernetes) if kubernetes is not None else None
            self.sandbox = Sandbox(runtime_container_image=runtime_img, base_container_image=base_img)

    return Cfg(k8s_namespace)


def make_dummy_event_llm():
    class Dummy:
        pass

    return Dummy(), Dummy()


def test_constructor_raises_when_no_kubernetes_config_and_add_shutdown_listener_called(monkeypatch):
    mod = importlib.import_module(MODULE_PATH)
    KubernetesRuntime = mod.KubernetesRuntime

    called = {}

    def fake_add_shutdown_listener(cb):
        # record that it was called and return an id
        called["called"] = True
        called["cb"] = cb
        return "fake-listener-id"

    monkeypatch.setattr(mod, "add_shutdown_listener", fake_add_shutdown_listener)

    # Ensure shutdown id is None so branch triggers
    KubernetesRuntime._shutdown_listener_id = None

    cfg = make_minimal_config(None)  # kubernetes is None -> should raise
    event_stream, llm_registry = make_dummy_event_llm()

    with pytest.raises(ValueError) as exc:
        KubernetesRuntime(cfg, event_stream, llm_registry, sid="s1")

    assert "Kubernetes configuration is required" in str(exc.value)
    # Ensure the add_shutdown_listener was called at start of __init__
    assert called.get("called") is True
    # The callback should be a callable (lambda) that references instance attributes (not executed here)
    assert callable(called.get("cb"))


def test_constructor_with_kubernetes_config_sets_values_and_calls_init_and_super(monkeypatch):
    mod = importlib.import_module(MODULE_PATH)
    KubernetesRuntime = mod.KubernetesRuntime

    # Spy for add_shutdown_listener
    listener = {"id": None, "cb": None}

    def fake_add_shutdown_listener(cb):
        listener["id"] = "listener-uuid"
        listener["cb"] = cb
        return listener["id"]

    monkeypatch.setattr(mod, "add_shutdown_listener", fake_add_shutdown_listener)

    # Replace _init_kubernetes_client to avoid real kubernetes interaction
    def fake_init_k8s_client():
        return ("fake-core-client", "fake-networking-client")

    monkeypatch.setattr(KubernetesRuntime, "_init_kubernetes_client", staticmethod(fake_init_k8s_client))

    # Replace ActionExecutionClient.__init__ to avoid its real initialization
    def fake_action_client_init(self, *args, **kwargs):
        # Record that it was called and store passed parameters for assertion
        self._ae_init_called = True
        self._ae_init_args = args
        self._ae_init_kwargs = kwargs
        # Try to set sid as the super would; sid is typically the 4th positional arg
        sid_val = None
        if len(args) >= 4:
            sid_val = args[3]
        elif "sid" in kwargs:
            sid_val = kwargs["sid"]
        # Fallback to None if not found
        self.sid = sid_val

    # The module exposes ActionExecutionClient; patch its __init__
    monkeypatch.setattr(mod.ActionExecutionClient, "__init__", fake_action_client_init, raising=True)

    # Prepare a config where runtime_container_image is empty -> fallback to base_container_image
    cfg = make_minimal_config("test-namespace")
    cfg.sandbox.runtime_container_image = ""  # empty, should fallback
    cfg.sandbox.base_container_image = "base-img:1.2.3"

    event_stream, llm_registry = make_dummy_event_llm()

    # Ensure shutdown id cleared to trigger add_shutdown_listener
    KubernetesRuntime._shutdown_listener_id = None

    inst = KubernetesRuntime(cfg, event_stream, llm_registry, sid="mysid", status_callback=lambda *a, **k: None)

    # Verify that add_shutdown_listener was registered and class var updated
    assert KubernetesRuntime._shutdown_listener_id == "listener-uuid"
    assert listener["cb"] is not None and callable(listener["cb"])

    # Verify initialization of important fields
    assert inst.config is cfg
    assert inst._runtime_initialized is False
    assert inst.status_callback is not None
    assert inst._k8s_namespace == "test-namespace"
    assert KubernetesRuntime._namespace == "test-namespace"

    # Verify that our fake k8s client values were set
    assert inst.k8s_client == "fake-core-client"
    assert inst.k8s_networking_client == "fake-networking-client"

    # runtime_container_image was empty so pod_image should be base image
    assert inst.pod_image == "base-img:1.2.3"

    # pod_name should include the sid
    assert "mysid" in inst.pod_name

    # api_url should include namespace and default port 8080
    assert ":8080" in inst.api_url
    assert ".test-namespace." in inst.api_url or ".test-namespace" in inst.k8s_local_url

    # Ensure that super (ActionExecutionClient) __init__ replacement was called
    assert getattr(inst, "_ae_init_called", False) is True
    # _ae_init_args first arg should be cfg (since super().__init__ forwarded same positional args)
    assert inst._ae_init_args[0] == cfg

    # Ensure the registered shutdown callback when called will call _cleanup_k8s_resources without error
    # Monkeypatch the cleanup to record call instead of doing real cleanup
    called_cleanup = {}

    def fake_cleanup(namespace, remove_pvc, conversation_id=""):
        called_cleanup["namespace"] = namespace
        called_cleanup["remove_pvc"] = remove_pvc
        called_cleanup["conversation_id"] = conversation_id

    monkeypatch.setattr(KubernetesRuntime, "_cleanup_k8s_resources", staticmethod(fake_cleanup))
    # Call the stored callback (simulating shutdown)
    listener["cb"]()

    assert called_cleanup["namespace"] == inst._k8s_namespace
    assert called_cleanup["remove_pvc"] is True
    # conversation_id refers to self.sid in the lambda; ensure it matches
    assert called_cleanup["conversation_id"] == inst.sid
