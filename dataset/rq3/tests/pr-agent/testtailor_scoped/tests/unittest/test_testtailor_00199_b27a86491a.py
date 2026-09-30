import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.agent.pr_agent')
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
        """Ensure that when a non-en-US response_language is set and a Dynabox-like
        setting exists with empty extra_instructions, the language instruction is assigned.
        """
        import asyncio
        import importlib
        import sys
        import types

        # Try to locate the module that defines PRAgent
        pr_module = None
        candidates = ["pr_agent.pr_agent", "pr_agent"]
        for name in candidates:
            try:
                m = importlib.import_module(name)
                if hasattr(m, "PRAgent"):
                    pr_module = m
                    break
            except Exception:
                continue
        # As a last resort, search loaded modules for one that has PRAgent
        if pr_module is None:
            for m in list(sys.modules.values()):
                try:
                    if hasattr(m, "PRAgent"):
                        pr_module = m
                        break
                except Exception:
                    continue

        if pr_module is None:
            self.fail("Could not find module containing PRAgent")

        # Save originals to restore later
        original_get_settings = getattr(pr_module, "get_settings", None)
        original_apply_repo_settings = getattr(pr_module, "apply_repo_settings", None)

        try:
            # Create a Dynabox-like class whose type string matches the expected check
            DynaBox = type("DynaBox", (), {})
            # Force the module path to mirror dynaconf.utils.boxing so str(type(obj)) matches
            DynaBox.__module__ = "dynaconf.utils.boxing"
            dynabox_instance = DynaBox()
            # Ensure extra_instructions exists and is falsy (None) so the branch sets it
            dynabox_instance.extra_instructions = None

            # Create a fake settings object compatible with minimal usage in _handle_request
            class FakeConfig:
                def __init__(self, response_language="fr-FR"):
                    self._response_language = response_language

                def get(self, key, default=None):
                    if key == "response_language":
                        return self._response_language
                    return default

            class FakeSettings:
                def __init__(self, dynabox_obj):
                    # the module iterates over get_settings(), so make it iterable over one key
                    self._keys = ["pr_reviewer"]
                    self._mapping = {"pr_reviewer": dynabox_obj}
                    self.config = FakeConfig(response_language="fr-FR")

                def __iter__(self):
                    return iter(self._keys)

                def get(self, key, default=None):
                    return self._mapping.get(key, default)

                # minimal API to avoid attribute errors if other code inspects settings
                def set(self, *args, **kwargs):
                    return None

                def unset(self, *args, **kwargs):
                    return None

                def as_dict(self):
                    return {"pr_reviewer": {"extra_instructions": None}}

            fake_settings = FakeSettings(dynabox_instance)

            # Monkeypatch the get_settings used in the module to return our fake settings
            pr_module.get_settings = lambda use_context=False: fake_settings

            # Monkeypatch apply_repo_settings to be a no-op to avoid heavy git provider logic
            pr_module.apply_repo_settings = lambda pr_url: None

            # Instantiate PRAgent and call _handle_request with an unknown command so the function
            # runs the settings modification logic and returns False before invoking heavy flows.
            agent = pr_module.PRAgent()
            # Use an unknown action so it will return False after processing settings
            request = ["unknown_command"]

            result = asyncio.get_event_loop().run_until_complete(
                agent._handle_request("http://example/pr/1", request)
            )

            # The handler should return False because the command is unknown
            self.assertFalse(result)

            # Verify that extra_instructions was set to the language instruction text
            response_language = fake_settings.config.get("response_language", "en-us")
            expected_text = f"Your response MUST be written in the language corresponding to locale code: '{response_language}'. This is crucial."
            self.assertEqual(dynabox_instance.extra_instructions, expected_text)

        finally:
            # Restore original functions to avoid side-effects on other tests
            if original_get_settings is not None:
                pr_module.get_settings = original_get_settings
            if original_apply_repo_settings is not None:
                pr_module.apply_repo_settings = original_apply_repo_settings
