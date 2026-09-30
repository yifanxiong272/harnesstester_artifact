import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.mosaico.env_bridge')
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
        """MODEL_MAX_TOKENS non-integer should hit the ValueError path and fall back to default."""
        import os
        from pr_agent.mosaico.env_bridge import apply_mosaico_env, DEFAULT_CUSTOM_MODEL_MAX_TOKENS
        from pr_agent.config_loader import get_settings, global_settings

        # Keys the env bridge touches; snapshot and restore to avoid global pollution.
        keys = [
            "OPENAI.API_BASE",
            "OPENAI.KEY",
            "CONFIG.MODEL",
            "CONFIG.FALLBACK_MODELS",
            "CONFIG.CUSTOM_MODEL_MAX_TOKENS",
            "LITELLM.SUCCESS_CALLBACK",
            "LITELLM.FAILURE_CALLBACK",
            "LITELLM.ENABLE_CALLBACKS",
        ]
        sentinel = object()
        snapshot = {k: global_settings.get(k, sentinel) for k in keys}

        prev_model_name = os.environ.get("MODEL_NAME")
        prev_model_max = os.environ.get("MODEL_MAX_TOKENS")
        # Ensure langfuse env not set so we don't get callback side-effects.
        prev_langfuse_host = os.environ.get("LANGFUSE_HOST")
        prev_langfuse_pub = os.environ.get("LANGFUSE_PUBLIC_KEY")
        prev_langfuse_sec = os.environ.get("LANGFUSE_SECRET_KEY")

        try:
            os.environ["MODEL_NAME"] = "my-model"               # must be present to enter model branch
            os.environ["MODEL_MAX_TOKENS"] = "not-an-int"       # triggers ValueError in int()
            for v in ("LANGFUSE_HOST", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"):
                os.environ.pop(v, None)

            apply_mosaico_env()

            assert get_settings().get("CONFIG.CUSTOM_MODEL_MAX_TOKENS") == DEFAULT_CUSTOM_MODEL_MAX_TOKENS
        finally:
            # restore settings
            for k, v in snapshot.items():
                if v is sentinel:
                    # best-effort reset to reasonable empties to avoid polluting global settings
                    if k.endswith("CALLBACK") or k == "CONFIG.FALLBACK_MODELS":
                        global_settings.set(k, [])
                    else:
                        global_settings.set(k, None)
                else:
                    global_settings.set(k, v)
            # restore env vars
            if prev_model_name is None:
                os.environ.pop("MODEL_NAME", None)
            else:
                os.environ["MODEL_NAME"] = prev_model_name
            if prev_model_max is None:
                os.environ.pop("MODEL_MAX_TOKENS", None)
            else:
                os.environ["MODEL_MAX_TOKENS"] = prev_model_max
            if prev_langfuse_host is None:
                os.environ.pop("LANGFUSE_HOST", None)
            else:
                os.environ["LANGFUSE_HOST"] = prev_langfuse_host
            if prev_langfuse_pub is None:
                os.environ.pop("LANGFUSE_PUBLIC_KEY", None)
            else:
                os.environ["LANGFUSE_PUBLIC_KEY"] = prev_langfuse_pub
            if prev_langfuse_sec is None:
                os.environ.pop("LANGFUSE_SECRET_KEY", None)
            else:
                os.environ["LANGFUSE_SECRET_KEY"] = prev_langfuse_sec
