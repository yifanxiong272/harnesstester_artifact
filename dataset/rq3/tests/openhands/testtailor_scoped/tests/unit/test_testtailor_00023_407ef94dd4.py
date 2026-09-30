import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.impl.remote.remote_runtime')
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
        """Ensure RemoteRuntime.__init__ calls its base __init__ (super().__init__)
        and that the code path reaches the API key validation (raising ValueError)."""
        # Prepare a flag to verify the base __init__ was invoked
        called = [False]

        # Prepare a minimal dummy config with sandbox attribute.
        class DummySandbox:
            pass

        class DummyConfig:
            pass

        config = DummyConfig()
        config.sandbox = DummySandbox()
        # Set api_key to None to trigger the ValueError in RemoteRuntime.__init__
        config.sandbox.api_key = None

        # Provide minimal placeholders for other constructor args
        event_stream = object()
        llm_registry = object()
        sid = "test-sid"

        # Monkeypatch the base class __init__ to a stub that records it was called
        base_cls = RemoteRuntime.__bases__[0]
        orig_init = getattr(base_cls, "__init__", None)

        def stub_base_init(
            self,
            config_arg,
            event_stream_arg,
            llm_registry_arg,
            sid_arg="default",
            plugins=None,
            env_vars=None,
            status_callback=None,
            attach_to_existing=False,
            headless_mode=True,
            user_id=None,
            git_provider_tokens=None,
        ):
            # Record that the stub was invoked and set minimal attributes
            called[0] = True
            self.config = config_arg
            self.sid = sid_arg
            # Provide a session object with headers that supports update()
            class Sess:
                pass

            self.session = Sess()
            self.session.headers = {}
            self.plugins = plugins or []
            self.attach_to_existing = attach_to_existing

        try:
            setattr(base_cls, "__init__", stub_base_init)

            # Construct RemoteRuntime and expect the ValueError about missing API key.
            with self.assertRaises(ValueError) as cm:
                RemoteRuntime(
                    config=config,
                    event_stream=event_stream,
                    llm_registry=llm_registry,
                    sid=sid,
                )

            # Verify the error message mentions API key requirement
            self.assertIn("API key is required to use the remote runtime", str(cm.exception))

            # Ensure the stubbed base __init__ was called (i.e., super().__init__ executed)
            self.assertTrue(called[0], "Base __init__ (super().__init__) was not invoked")

        finally:
            # Restore original base __init__
            if orig_init is not None:
                setattr(base_cls, "__init__", orig_init)
