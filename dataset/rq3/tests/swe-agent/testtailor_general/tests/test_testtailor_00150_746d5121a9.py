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
        """Ensure that when extra.test_run is true, the agent model_name is overridden
        to "instant_empty_submit" and the /run endpoint returns 202.
        """
        # prepare a minimal runConfig that will be accepted (default config fills the rest)
        run_config = {
            "environment": {
                "image_name": "some-image",
                "script": "echo hi",
                "repo_path": ".",
                "base_commit": "HEAD",
            },
            "agent": {"model": {"model_name": "original_model"}},
            "extra": {"test_run": True},
            "problem_statement": {"input": "do something", "type": "text"},
        }

        created = []
        validated = {}

        class DummyMainThread:
            def __init__(self, settings, wu):
                # capture the settings for assertions
                self.settings = settings
                created.append(self)

            def start(self):
                # don't actually start any background work in tests
                self.started = True

        # fake model_validate to capture the validated config dict and return
        # a simple settings object that exposes agent.model.model_name
        def fake_model_validate(**kwargs):
            validated.update(kwargs)
            # Build a minimal settings-like object
            from types import SimpleNamespace

            settings_obj = SimpleNamespace()
            settings_obj.agent = SimpleNamespace()
            settings_obj.agent.model = SimpleNamespace(
                model_name=kwargs["agent"]["model"]["model_name"]
            )
            return settings_obj

        # Patch the MainThread and RunSingleConfig.model_validate used by the /run handler
        with patch("sweagent.api.server.MainThread", DummyMainThread):
            with patch("sweagent.run.run_single.RunSingleConfig.model_validate", new=fake_model_validate):
                with app.test_client() as client:
                    with app.app_context():
                        response = client.get(
                            "/run", query_string={"runConfig": json.dumps(run_config)}
                        )

        # endpoint should respond with 202 and the expected message
        assert response.status_code == 202
        assert b"Commands are being executed" in response.data

        # Our DummyMainThread should have been instantiated once
        assert len(created) == 1
        settings = created[0].settings

        # The validated dict (what would be passed into model_validate) should have the overridden model_name
        assert validated["agent"]["model"]["model_name"] == "instant_empty_submit"

        # And the settings object returned by our fake_model_validate should reflect that as well
        assert getattr(settings, "agent").model.model_name == "instant_empty_submit"
