import types
import pytest
import importlib

from pr_agent.algo.ai_handlers import openai_ai_handler as handler_mod

# Small test helpers and deterministic fake settings/provider objects
class _FakeOpenAI:
    def __init__(self, key=None, org=None, api_type=None, api_version=None, api_base=None):
        self.key = key
        self.org = org
        self.api_type = api_type
        self.api_version = api_version
        self.api_base = api_base

class _FakeSettings:
    def __init__(self, openai):
        # openai can be None to simulate missing attribute access
        self.openai = openai

    def get(self, key, default=None):
        # Mirror the minimal behaviour expected by the implementation: return
        # the corresponding openai attribute or the default
        if self.openai is None:
            return default
        if key == "OPENAI.ORG":
            return self.openai.org if getattr(self.openai, "org", None) is not None else default
        if key == "OPENAI.API_TYPE":
            return self.openai.api_type if getattr(self.openai, "api_type", None) is not None else default
        if key == "OPENAI.API_VERSION":
            return self.openai.api_version if getattr(self.openai, "api_version", None) is not None else default
        if key == "OPENAI.API_BASE":
            return self.openai.api_base if getattr(self.openai, "api_base", None) is not None else default
        return default


def _patch_module_for_test(mod, openai_obj, settings_obj):
    """Patch the handler module in-place to control its collaborators.

    Returns an 'orig' dict that can be used to restore the original symbols.
    """
    orig = {
        "openai": mod.openai,
        "environ": mod.environ,
        "get_settings": mod.get_settings,
        "base_init": getattr(mod.BaseAiHandler, "__init__", None),
    }

    # Replace openai object with a SimpleNamespace-like holder so attributes are settable
    mod.openai = openai_obj
    # Replace the imported environ reference (module-level) with a fresh dict for isolation
    mod.environ = {}
    # Provide deterministic get_settings() returning our fake settings object
    mod.get_settings = lambda: settings_obj

    # Patch the BaseAiHandler.__init__ used by super().__init__() to avoid unknown side effects
    def _noop_init(self):
        return None

    mod.BaseAiHandler.__init__ = _noop_init

    return orig


def _restore_module_after_test(mod, orig):
    mod.openai = orig["openai"]
    mod.environ = orig["environ"]
    mod.get_settings = orig["get_settings"]
    # restore original base initializer (could be None)
    if orig["base_init"] is None:
        try:
            delattr(mod.BaseAiHandler, "__init__")
        except Exception:
            pass
    else:
        mod.BaseAiHandler.__init__ = orig["base_init"]


def test_init_all_options_round_105():
    """Exercise branches: ORG present, API_TYPE azure, API_VERSION and API_BASE present.

    Assertions check environment variables, module-level openai attributes, and handler.azure flag.
    """
    # prepare module-level openai holder
    openai_holder = types.SimpleNamespace(organization=None, azure_key=None, api_version=None, api_base=None)

    fake_openai = _FakeOpenAI(key="KEY123", org="org-xyz", api_type="azure", api_version="2024-01-01", api_base="https://example.com/base")
    fake_settings = _FakeSettings(fake_openai)

    orig = _patch_module_for_test(handler_mod, openai_holder, fake_settings)
    try:
        h = handler_mod.OpenAIHandler()

        # Key must be set in the module environ mapping
        assert handler_mod.environ["OPENAI_API_KEY"] == "KEY123"
        # ORGANIZATION assignment must be applied to the patched openai holder
        assert handler_mod.openai.organization == "org-xyz"
        # azure path: handler.azure set and azure_key populated
        assert getattr(h, "azure", False) is True
        assert handler_mod.openai.azure_key == "KEY123"
        # API version must be forwarded
        assert handler_mod.openai.api_version == "2024-01-01"
        # API_BASE should populate OPENAI_BASE_URL env
        assert handler_mod.environ["OPENAI_BASE_URL"] == "https://example.com/base"
    finally:
        _restore_module_after_test(handler_mod, orig)


def test_init_minimal_settings_round_105():
    """Exercise path where only OPENAI key exists and optional settings are absent.

    Asserts that optional branches are skipped and no 'azure' attribute is created on the instance.
    """
    openai_holder = types.SimpleNamespace(organization=None, azure_key=None, api_version=None, api_base=None)

    fake_openai = _FakeOpenAI(key="MINKEY")
    fake_settings = _FakeSettings(fake_openai)

    orig = _patch_module_for_test(handler_mod, openai_holder, fake_settings)
    try:
        h = handler_mod.OpenAIHandler()

        # Only the key is placed; optional env keys are not present
        assert handler_mod.environ["OPENAI_API_KEY"] == "MINKEY"
        assert "OPENAI_BASE_URL" not in handler_mod.environ
        # No organization should be assigned
        assert handler_mod.openai.organization is None
        # No azure attribute should be present on the handler
        assert not hasattr(h, "azure")
    finally:
        _restore_module_after_test(handler_mod, orig)


def test_missing_openai_key_raises_valueerror_round_105():
    """Simulate get_settings().openai being None which leads to an AttributeError and thus a ValueError.

    This covers the exception handling branch in the constructor.
    """
    openai_holder = types.SimpleNamespace(organization=None, azure_key=None, api_version=None, api_base=None)

    # Provide settings that will cause an AttributeError when the code tries to access .openai.key
    fake_settings = _FakeSettings(None)

    orig = _patch_module_for_test(handler_mod, openai_holder, fake_settings)
    try:
        with pytest.raises(ValueError) as excinfo:
            handler_mod.OpenAIHandler()
        assert "OpenAI key is required" in str(excinfo.value)
    finally:
        _restore_module_after_test(handler_mod, orig)
