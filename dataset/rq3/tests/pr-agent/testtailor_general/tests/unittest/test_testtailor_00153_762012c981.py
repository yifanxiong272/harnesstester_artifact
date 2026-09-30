import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.algo.ai_handlers.litellm_ai_handler')
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
    def test_imds_region_resolution_exception_logs_warning(self):
        """When AWS_USE_IMDS is true and session.region_name access raises an exception,
        the handler should catch it and log a warning containing the failure message."""
        # Ensure IMDS is enabled and no AWS_REGION_NAME in env
        os.environ["AWS_USE_IMDS"] = "true"
        os.environ.pop("AWS_REGION_NAME", None)

        # Minimal settings object to satisfy LiteLLMAIHandler.__init__ usage
        Config = type("Config", (), {
            "reasoning_effort": None,
            "ai_timeout": 30,
            "custom_reasoning_model": False,
            "max_model_tokens": 32000,
            "verbosity_level": 0,
            "seed": -1,
            "get": lambda self, key, default=None: default,
        })
        Litellm = type("Litellm", (), {
            "get": lambda self, key, default=None: default,
        })
        settings = type("Settings", (), {
            "config": Config(),
            "litellm": Litellm(),
            "get": lambda self, key, default=None: default,
        })()

        # Prepare frozen credentials returned by boto3 so IMDS mode is entered
        frozen = MagicMock()
        frozen.access_key = "FAKEKEY"
        frozen.secret_key = "FAKESECRET"
        frozen.token = None

        class FaultySession:
            def get_credentials(self):
                mock_creds = MagicMock()
                mock_creds.get_frozen_credentials.return_value = frozen
                return mock_creds

            @property
            def region_name(self):
                # Simulate an unexpected error when attempting to resolve region
                raise RuntimeError("region lookup failed")

        faulty_session = FaultySession()

        logger_instance = MagicMock()
        # Patch boto3.Session to return our faulty session and patch get_settings/get_logger
        with patch("boto3.Session", return_value=faulty_session), \
             patch("pr_agent.algo.ai_handlers.litellm_ai_handler.get_settings", return_value=settings), \
             patch("pr_agent.algo.ai_handlers.litellm_ai_handler.get_logger", return_value=logger_instance):
            # The constructor should not raise despite the region resolution error
            handler = LiteLLMAIHandler()

            # Verify that a warning was logged about failing to resolve the region
            self.assertTrue(logger_instance.warning.called, "Expected a warning to be logged for region resolution failure")
            warning_msg = logger_instance.warning.call_args[0][0]
            self.assertIn("AWS_USE_IMDS: failed to resolve region via boto3", warning_msg)
            self.assertIn("region lookup failed", warning_msg)
