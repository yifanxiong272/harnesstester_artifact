import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.builder.remote')
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
        """Ensure RemoteRuntimeBuilder.build executes the tar creation and returns image on SUCCESS."""
        # Use __import__ to avoid top-level import statements in this snippet
        os = __import__('os')
        tempfile = __import__('tempfile')

        # Create a temporary build context directory with a small Dockerfile
        tmp_dir_ctx = tempfile.TemporaryDirectory()
        try:
            dummy_file_path = os.path.join(tmp_dir_ctx.name, "Dockerfile")
            with open(dummy_file_path, "w") as f:
                f.write("FROM alpine:3.18\nCMD [\"true\"]\n")

            # Dummy response and session to avoid real HTTP calls
            class DummyResponse:
                def __init__(self, status_code: int, json_data: dict, text: str = ""):
                    self.status_code = status_code
                    self._json = json_data
                    self.text = text

                def raise_for_status(self):
                    # No-op to simulate successful status
                    return None

                def json(self):
                    return self._json

                def close(self):
                    return None

            class DummySession:
                def __init__(self):
                    self.headers = {}

                def request(self, method, url, timeout=None, **kwargs):
                    # Simulate POST to /build -> returns build_id
                    if method == "POST" and url.endswith("/build"):
                        return DummyResponse(200, {"build_id": "build-123"})
                    # Simulate GET to /build_status -> returns success immediately
                    if method == "GET" and url.endswith("/build_status"):
                        return DummyResponse(200, {"status": "SUCCESS", "image": "repo/image:latest"})
                    # Fallback
                    return DummyResponse(404, {"detail": "not found"}, text="not found")

            # Instantiate the builder with the dummy session and call build
            builder = RemoteRuntimeBuilder(api_url="http://example.com", api_key="key", session=DummySession())
            result = builder.build(path=tmp_dir_ctx.name, tags=["repo/image:latest"])

            # Verify the returned image string matches the status response
            self.assertEqual(result, "repo/image:latest")
        finally:
            tmp_dir_ctx.cleanup()
