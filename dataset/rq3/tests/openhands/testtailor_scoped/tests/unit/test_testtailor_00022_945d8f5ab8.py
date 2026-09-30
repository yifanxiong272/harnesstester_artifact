import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.impl.kubernetes.kubernetes_runtime')
except Exception:
    _testtailor_target = None
else:
    globals().update({
        name: value
        for name, value in vars(_testtailor_target).items()
        if not name.startswith("__")
    })

class _TestTailorTimeout:
    @staticmethod
    def timeout(_seconds):
        return lambda function: function

timeout_decorator = _TestTailorTimeout()

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_case_XX(self):
        """Ensure that when no shutdown listener exists, KubernetesRuntime registers one
        via add_shutdown_listener and that the registered callable invokes the cleanup
        function with the instance's namespace and sid.
        """
        # Local imports for the test
        from types import SimpleNamespace
        from unittest import mock
        import openhands.utils.shutdown_listener as sl
        from openhands.runtime.impl.kubernetes.kubernetes_runtime import (
            KubernetesRuntime,
        )

        # Keep originals to restore later
        original_shutdown_id = KubernetesRuntime._shutdown_listener_id
        original_listeners = sl._shutdown_listeners.copy()

        # Prepare a minimal config object with required attributes
        fake_k8s_config = SimpleNamespace(
            namespace="test-ns",
            ingress_domain="example.com",
            resource_memory_limit="256Mi",
            resource_cpu_request="100m",
            resource_memory_request="128Mi",
            pvc_storage_size="1Gi",
            pvc_storage_class=None,
            image_pull_secret=None,
            node_selector_key=None,
            node_selector_val=None,
            tolerations_yaml=None,
            ingress_tls_secret=None,
            privileged=False,
        )
        fake_sandbox = SimpleNamespace(
            runtime_container_image="test-image:latest",
            base_container_image="fallback-image:latest",
            runtime_startup_env_vars={},
            keep_runtime_alive=False,
        )
        fake_config = SimpleNamespace(
            kubernetes=fake_k8s_config,
            sandbox=fake_sandbox,
            debug=False,
            workspace_mount_path_in_sandbox="/workspace",
        )

        # Ensure no shutdown listener exists before instantiation to hit the branch
        KubernetesRuntime._shutdown_listener_id = None
        sl._shutdown_listeners.clear()

        # Patch external interactions:
        # - _init_kubernetes_client to avoid real k8s calls
        # - the base class __init__ to avoid heavy initialization
        # - _cleanup_k8s_resources to observe invocation when the listener is called
        base_cls = KubernetesRuntime.__bases__[0]
        with mock.patch.object(
            KubernetesRuntime, "_init_kubernetes_client", return_value=(mock.Mock(), mock.Mock())
        ), mock.patch.object(base_cls, "__init__", return_value=None), mock.patch.object(
            KubernetesRuntime, "_cleanup_k8s_resources", new=mock.Mock()
        ) as cleanup_mock:
            # Instantiate the runtime; this should register a shutdown listener
            rt = KubernetesRuntime(
                config=fake_config,
                event_stream=mock.Mock(),
                llm_registry=mock.Mock(),
                sid="my-sid",
            )

            # Because we patched the base __init__, the instance may not have attributes that
            # would normally be set there. Provide them now so the lambda (capturing `self`)
            # can access them when invoked.
            rt.sid = "my-sid"
            rt._k8s_namespace = "test-ns"
            KubernetesRuntime._namespace = "test-ns"

            # After init, a shutdown listener id should be set on the class
            self.assertIsNotNone(
                KubernetesRuntime._shutdown_listener_id,
                "Expected KubernetesRuntime._shutdown_listener_id to be set",
            )

            # The listener should be present in the global listeners mapping
            sid_key = KubernetesRuntime._shutdown_listener_id
            self.assertIn(
                sid_key,
                sl._shutdown_listeners,
                "Registered shutdown listener not found in shutdown listener registry",
            )

            # Invoke the registered listener callable and assert cleanup was called
            listener_callable = sl._shutdown_listeners[sid_key]
            listener_callable()  # simulate Ctrl+C / shutdown

            cleanup_mock.assert_called_once_with(
                namespace="test-ns", remove_pvc=True, conversation_id="my-sid"
            )

        # Restore original state
        sl._shutdown_listeners.clear()
        sl._shutdown_listeners.update(original_listeners)
        KubernetesRuntime._shutdown_listener_id = original_shutdown_id
