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
    def test_case_XX(self):
        """When AWS_USE_IMDS is true but boto3 returns no creds, static settings
        including AWS_SESSION_TOKEN are exported to the environment (target line)."""
        # Enable IMDS path
        os.environ["AWS_USE_IMDS"] = "true"

        # Prepare settings that supply static AWS creds including a session token
        mapping = {
            "aws.AWS_ACCESS_KEY_ID": "STATICKEY",
            "aws.AWS_SECRET_ACCESS_KEY": "STATICSECRET",
            "aws.AWS_REGION_NAME": "us-east-1",
            "aws.AWS_SESSION_TOKEN": "STATIC-SESSION-TOKEN",
        }

        def _get(key, default=None):
            return mapping.get(key, default)

        # Build a minimal settings object compatible with get_settings() usage
        settings = type("Settings", (), {})()
        settings.get = _get
        settings.aws = type("AWS", (), {
            "AWS_ACCESS_KEY_ID": mapping["aws.AWS_ACCESS_KEY_ID"],
            "AWS_SECRET_ACCESS_KEY": mapping["aws.AWS_SECRET_ACCESS_KEY"],
            "AWS_REGION_NAME": mapping["aws.AWS_REGION_NAME"],
            "AWS_SESSION_TOKEN": mapping["aws.AWS_SESSION_TOKEN"],
        })()
        settings.config = type("Config", (), {
            "reasoning_effort": None,
            "ai_timeout": 30,
            "custom_reasoning_model": False,
            "max_model_tokens": 32000,
            "verbosity_level": 0,
            "seed": -1,
            "get": lambda self, key, default=None: default,
        })()
        settings.litellm = type("Litellm", (), {
            "get": lambda self, key, default=None: default,
        })()

        # boto3.Session should exist but return no credentials to force the static-path branch
        mock_session = MagicMock()
        mock_session.get_credentials.return_value = None
        mock_session.region_name = None

        # Patch get_settings and boto3.Session during handler init using string targets
        with patch('pr_agent.algo.ai_handlers.litellm_ai_handler.get_settings', return_value=settings), \
             patch("boto3.Session", return_value=mock_session):
            handler = LiteLLMAIHandler()

        try:
            # Verify static creds were applied to the environment, including session token
            self.assertEqual(os.environ.get("AWS_ACCESS_KEY_ID"), "STATICKEY")
            self.assertEqual(os.environ.get("AWS_SECRET_ACCESS_KEY"), "STATICSECRET")
            self.assertEqual(os.environ.get("AWS_REGION_NAME"), "us-east-1")
            # TARGET: ensure AWS_SESSION_TOKEN was written from static settings
            self.assertEqual(os.environ.get("AWS_SESSION_TOKEN"), "STATIC-SESSION-TOKEN")
            # And handler is not in IMDS ambient mode
            self.assertFalse(handler._aws_imds_mode)
            # Static creds should be stashed for potential fallback
            self.assertIsNotNone(handler._aws_static_creds)
            self.assertEqual(handler._aws_static_creds["AWS_SESSION_TOKEN"], "STATIC-SESSION-TOKEN")
        finally:
            # Clean up environment to avoid leaking to other tests
            for k in ("AWS_USE_IMDS", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION_NAME", "AWS_SESSION_TOKEN"):
                os.environ.pop(k, None)
