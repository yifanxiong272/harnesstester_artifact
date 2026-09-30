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
        """Verify that KubernetesRuntime registers a shutdown listener when none exists
        and that the registered callable calls _cleanup_k8s_resources with the proper args.
        """
        # Import modules dynamically to avoid adding import statements at top-level
        runtime_module = __import__('openhands.runtime', fromlist=['KubernetesRuntime'])
        shutdown_mod = __import__('openhands.utils.shutdown_listener', fromlist=['_shutdown_listeners'])

        KubernetesRuntime = runtime_module.KubernetesRuntime
        BaseClass = KubernetesRuntime.__bases__[0]

        # Backup originals
        orig_cleanup = KubernetesRuntime._cleanup_k8s_resources
        orig_init_k8s_client = getattr(KubernetesRuntime, '_init_kubernetes_client', None)
        orig_base_init = BaseClass.__init__
        orig_listeners = dict(getattr(shutdown_mod, '_shutdown_listeners', {}))

        # Ensure clean state
        KubernetesRuntime._shutdown_listener_id = None
        shutdown_mod._shutdown_listeners.clear()

        cleanup_called = {}

        # Fake cleanup that records arguments
        def fake_cleanup(namespace: str, remove_pvc: bool = False, conversation_id: str = ''):
            cleanup_called['namespace'] = namespace
            cleanup_called['remove_pvc'] = remove_pvc
            cleanup_called['conversation_id'] = conversation_id

        # Fake k8s client initializer to avoid requiring a real cluster
        def fake_init_k8s_client():
            types_mod = __import__('types')
            return (types_mod.SimpleNamespace(), types_mod.SimpleNamespace())

        # Stub the base class __init__ to avoid heavy parent initialization
        def fake_base_init(self, *args, **kwargs):
            # super().__init__ signature in call: config, event_stream, llm_registry, sid, ...
            if len(args) >= 4:
                self.sid = args[3]
            else:
                self.sid = kwargs.get('sid', 'default')
            # minimal attributes used later
            self.plugins = kwargs.get('plugins') or (args[4] if len(args) > 4 else [])
            self.attach_to_existing = kwargs.get('attach_to_existing', False)

        # Apply monkeypatches
        KubernetesRuntime._cleanup_k8s_resources = staticmethod(fake_cleanup)
        KubernetesRuntime._init_kubernetes_client = staticmethod(fake_init_k8s_client)
        BaseClass.__init__ = fake_base_init

        try:
            # Build minimal config objects expected by KubernetesRuntime.__init__
            types_mod = __import__('types')
            SimpleNamespace = types_mod.SimpleNamespace

            k8s_cfg = SimpleNamespace(
                namespace='test-namespace',
                ingress_domain='example.com',
                ingress_tls_secret=None,
                node_selector_key=None,
                node_selector_val=None,
                tolerations_yaml=None,
                pvc_storage_size='1Gi',
                pvc_storage_class=None,
                resource_memory_limit='512Mi',
                resource_cpu_request='100m',
                resource_memory_request='128Mi',
                image_pull_secret=None,
                privileged=False,
            )
            sandbox_cfg = SimpleNamespace(
                runtime_container_image='',
                base_container_image='base/image:latest',
                runtime_startup_env_vars={},
                keep_runtime_alive=False,
            )
            config = SimpleNamespace(
                kubernetes=k8s_cfg,
                sandbox=sandbox_cfg,
                workspace_mount_path_in_sandbox='/workspace',
                debug=False,
            )

            # Instantiate runtime (this should register a shutdown listener in shutdown_mod._shutdown_listeners)
            rt = KubernetesRuntime(
                config=config,
                event_stream=None,
                llm_registry=None,
                sid='mysid',
                plugins=[],
                env_vars=None,
                status_callback=None,
                attach_to_existing=False,
                headless_mode=True,
                user_id=None,
                git_provider_tokens=None,
            )

            # There should be exactly one new shutdown listener registered in the module dict
            listeners = shutdown_mod._shutdown_listeners
            self.assertTrue(len(listeners) >= 1, f'Expected at least one shutdown listener, got: {listeners}')

            # Find the listener that corresponds to the instance we just created.
            # The constructor stores the returned id into KubernetesRuntime._shutdown_listener_id.
            listener_id = KubernetesRuntime._shutdown_listener_id
            self.assertIn(listener_id, listeners, 'KubernetesRuntime._shutdown_listener_id should be present in shutdown listeners')

            listener_callable = listeners[listener_id]
            self.assertTrue(callable(listener_callable), 'Registered shutdown listener should be callable')

            # Invoke the registered callable; it should call our fake_cleanup with expected args
            listener_callable()
            self.assertEqual(cleanup_called.get('namespace'), 'test-namespace')
            self.assertTrue(cleanup_called.get('remove_pvc'))
            self.assertEqual(cleanup_called.get('conversation_id'), 'mysid')

        finally:
            # Restore originals and listeners
            KubernetesRuntime._cleanup_k8s_resources = orig_cleanup
            if orig_init_k8s_client is None:
                try:
                    delattr(KubernetesRuntime, '_init_kubernetes_client')
                except Exception:
                    pass
            else:
                KubernetesRuntime._init_kubernetes_client = orig_init_k8s_client

            BaseClass.__init__ = orig_base_init

            # Restore listeners to original state
            shutdown_mod._shutdown_listeners.clear()
            shutdown_mod._shutdown_listeners.update(orig_listeners)

            KubernetesRuntime._shutdown_listener_id = None
