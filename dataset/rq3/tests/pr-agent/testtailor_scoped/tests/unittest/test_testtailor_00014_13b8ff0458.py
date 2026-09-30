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
        """Ensure that setting LITELLM.DISABLE_AIOHTTP causes the handler to disable aiohttp transport."""
        settings = get_settings()

        # Preserve original state to restore after the test
        orig_LITELLM = getattr(settings, "LITELLM", None)
        orig_litellm_attr = getattr(settings, "litellm", None)
        orig_flag = getattr(litellm, "disable_aiohttp_transport", None)

        try:
            # Ensure the LITELLM entry is a dict so Dynaconf.get(... dotted ...) can call .get on it
            settings.LITELLM = {"DISABLE_AIOHTTP": True}

            # Ensure starting global state is not already set to True to avoid false positives
            litellm.disable_aiohttp_transport = False

            # Act: instantiate the handler which reads settings during __init__
            handler = LiteLLMAIHandler()

            # Assert: instantiation should set the global flag on litellm
            self.assertTrue(
                litellm.disable_aiohttp_transport,
                "Expected aiohttp transport to be disabled by settings"
            )
        finally:
            # Restore original settings to avoid leaking state between tests
            if orig_LITELLM is None:
                try:
                    delattr(settings, "LITELLM")
                except Exception:
                    pass
            else:
                settings.LITELLM = orig_LITELLM

            if orig_litellm_attr is None:
                try:
                    delattr(settings, "litellm")
                except Exception:
                    pass
            else:
                settings.litellm = orig_litellm_attr

            if orig_flag is None:
                try:
                    delattr(litellm, "disable_aiohttp_transport")
                except Exception:
                    pass
            else:
                litellm.disable_aiohttp_transport = orig_flag
