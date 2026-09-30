import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.api.server')
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
        """Ensure that existing alive threads have stop() called when /run is invoked."""
        # Local imports to comply with the task constraints
        import json
        import tempfile
        import shutil
        from pathlib import Path
        import yaml
        from sweagent.api import server

        app = server.app

        # Prepare a dummy existing thread that reports alive and records stop() calls
        class DummyExistingThread:
            def __init__(self):
                self.stopped = False
                self.alive_checked = False

            def is_alive(self):
                # record that is_alive was queried
                self.alive_checked = True
                return True

            def stop(self):
                self.stopped = True

        dummy_thread = DummyExistingThread()

        # Replace MainThread with a dummy to avoid starting the real background work
        class DummyMainThread:
            def __init__(self, settings, wu):
                self.settings = settings
                self.wu = wu
                self.started = False

            def start(self):
                self.started = True

        # Create a dummy settings object to be returned by the patched model_validate
        class DummySettings:
            pass

        # Backup and patch globals
        old_threads = server.THREADS.copy()
        old_MainThread = getattr(server, "MainThread", None)
        old_model_validate = getattr(server.RunSingleConfig, "model_validate", None)
        old_config_dir = getattr(server, "CONFIG_DIR", None)
        tmpdir = tempfile.mkdtemp()
        try:
            # Ensure there's a default.yaml so the handler does not raise FileNotFoundError
            Path(tmpdir, "default.yaml").write_text(yaml.safe_dump({}))
            server.CONFIG_DIR = Path(tmpdir)

            server.THREADS.clear()
            server.THREADS["existing"] = dummy_thread
            server.MainThread = DummyMainThread

            # Patch RunSingleConfig.model_validate to accept kwargs and return a DummySettings instance
            server.RunSingleConfig.model_validate = classmethod(lambda cls, **kwargs: DummySettings())

            # Minimal runConfig that provides the fields accessed by the endpoint
            run_config = {
                "environment": {
                    "image_name": "img",
                    "script": "script.sh",
                    "repo_path": ".",
                    "base_commit": "HEAD",
                },
                "agent": {"model": {"model_name": "test-model"}},
                "extra": {"test_run": False},
                "problem_statement": {"input": "desc", "type": "text"},
            }

            # Use a request context so session/request are available when calling the view directly
            query = {"runConfig": json.dumps(run_config)}
            with app.test_request_context("/run", query_string=query, method="GET"):
                # Call the run view directly
                resp = server.run()

            # The existing thread should have had stop() called
            assert dummy_thread.alive_checked is True, "is_alive() was not queried on existing thread"
            assert dummy_thread.stopped is True, "stop() was not called on existing thread"

            # The endpoint should accept the request and return 202 (thread started)
            # server.run returns a tuple (message, status) or a Response; handle both
            if isinstance(resp, tuple):
                assert resp[1] == 202
            else:
                # Werkzeug Response
                assert getattr(resp, "status_code", None) == 202
        finally:
            # Restore patched globals
            server.THREADS.clear()
            server.THREADS.update(old_threads)
            if old_MainThread is not None:
                server.MainThread = old_MainThread
            if old_model_validate is not None:
                server.RunSingleConfig.model_validate = old_model_validate
            if old_config_dir is not None:
                server.CONFIG_DIR = old_config_dir
            shutil.rmtree(tmpdir)
