import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.storage.web_hook')
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
        """Ensure __init__ sets file_store, base_url, and client correctly."""
        class DummyFileStore(FileStore):
            def __init__(self):
                self._store = {}

            def write(self, path: str, contents: str | bytes) -> None:
                self._store[path] = contents

            def read(self, path: str) -> str:
                return self._store[path]

            def list(self, path: str) -> list[str]:
                return list(self._store.keys())

            def delete(self, path: str) -> None:
                self._store.pop(path, None)

        store = DummyFileStore()
        base_url = "https://example.test/hooks/"

        # Case 1: provide an explicit client object and ensure it's assigned unchanged
        sentinel_client = object()
        wh = WebHookFileStore(store, base_url, client=sentinel_client)
        self.assertIs(wh.file_store, store)
        self.assertEqual(wh.base_url, base_url)
        self.assertIs(wh.client, sentinel_client)

        # Case 2: pass None to trigger creation of a new httpx.Client
        wh_auto = WebHookFileStore(store, base_url, client=None)
        # httpx should be available in the test environment (module-level import)
        self.assertIs(wh_auto.file_store, store)
        self.assertEqual(wh_auto.base_url, base_url)
        self.assertIsInstance(wh_auto.client, httpx.Client)
