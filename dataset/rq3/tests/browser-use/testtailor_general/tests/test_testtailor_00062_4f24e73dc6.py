import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.groq.chat')
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
        """Ensure ChatGroq.get_client instantiates AsyncGroq with the expected parameters."""
        # Get the module where ChatGroq is defined using built-in __import__
        mod = __import__(ChatGroq.__module__, fromlist=['*'])

        # Keep original to restore after test
        original_asyncgroq = getattr(mod, "AsyncGroq", None)

        # Spy / dummy replacement to capture constructor arguments
        class DummyAsyncGroq:
            def __init__(self, api_key=None, base_url=None, timeout=None, max_retries=None):
                # store values for assertions
                self._init_kwargs = {
                    "api_key": api_key,
                    "base_url": base_url,
                    "timeout": timeout,
                    "max_retries": max_retries,
                }

        try:
            # Patch the module's AsyncGroq with our dummy
            setattr(mod, "AsyncGroq", DummyAsyncGroq)

            # Create a ChatGroq instance with explicit client-init parameters
            cg = ChatGroq(
                model="test-model",
                api_key="test-key-123",
                base_url="https://api.example",
                timeout=3.14,
                max_retries=7,
            )

            # Call the method under test
            client = cg.get_client()

            # Assertions: the returned object should be our dummy and captured args match
            self.assertIsInstance(client, DummyAsyncGroq)
            self.assertEqual(client._init_kwargs["api_key"], "test-key-123")
            self.assertEqual(client._init_kwargs["base_url"], "https://api.example")
            self.assertEqual(client._init_kwargs["timeout"], 3.14)
            self.assertEqual(client._init_kwargs["max_retries"], 7)

        finally:
            # Restore original AsyncGroq to not affect other tests
            if original_asyncgroq is None:
                if hasattr(mod, "AsyncGroq"):
                    delattr(mod, "AsyncGroq")
            else:
                setattr(mod, "AsyncGroq", original_asyncgroq)
