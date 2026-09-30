import importlib
import sys
import types
import builtins
import pytest
from unittest import mock


def _make_fake_google(genai_client_cls):
    """Helper to install a fake 'google' package with a genai submodule.

    Returns a tuple of (google_module, genai_module) so the caller can clean up sys.modules.
    """
    google_mod = types.ModuleType("google")
    genai_mod = types.ModuleType("genai")
    genai_mod.Client = genai_client_cls
    google_mod.genai = genai_mod
    sys.modules["google"] = google_mod
    sys.modules["google.genai"] = genai_mod
    return google_mod, genai_mod


def _cleanup_fake_google():
    for name in ("google.genai", "google"):
        if name in sys.modules:
            del sys.modules[name]


def test_ensure_client_success_round_118():
    """When google.genai.Client is present and constructs normally, _ensure_client sets _client and logs info."""
    m = importlib.import_module("gpt_researcher.llm_provider.image.image_generator")
    ImageGeneratorProvider = m.ImageGeneratorProvider

    class FakeClient:
        def __init__(self, api_key):
            # store api_key to assert it was passed through
            self.api_key = api_key

    # install fake google.genai
    _make_fake_google(FakeClient)

    # replace module logger with a Mock to capture info calls
    mock_logger = mock.Mock()
    m.logger = mock_logger

    try:
        provider = ImageGeneratorProvider("my-model", "key-123", output_dir=".")
        # ensure client is None to hit the import branch
        provider._client = None
        provider.api_key = "key-123"
        provider.model_name = "my-model"

        provider._ensure_client()

        # provider._client should be instance of our FakeClient
        assert isinstance(provider._client, FakeClient)
        assert provider._client.api_key == "key-123"

        # logger.info should have been called with an initialization message
        mock_logger.info.assert_called()
        info_msg = mock_logger.info.call_args[0][0]
        assert "Initialized image generation with model" in info_msg
        assert "my-model" in info_msg
    finally:
        # clean up injected modules
        _cleanup_fake_google()


def test_ensure_client_importerror_round_118():
    """If importing google.genai fails, _ensure_client raises the packaged ImportError with guidance text."""
    m = importlib.import_module("gpt_researcher.llm_provider.image.image_generator")
    ImageGeneratorProvider = m.ImageGeneratorProvider

    # monkeypatch builtins.__import__ to raise ImportError for google imports
    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "google" or (fromlist and "genai" in fromlist):
            raise ImportError("no google available")
        return orig_import(name, globals, locals, fromlist, level)

    builtins.__import__ = fake_import

    try:
        provider = ImageGeneratorProvider("mm", "kk", output_dir=".")
        provider._client = None
        provider.api_key = "kk"

        with pytest.raises(ImportError) as excinfo:
            provider._ensure_client()

        # The module raises an ImportError with guidance text when google-genai is not available
        assert "google-genai package is required for image generation" in str(excinfo.value)
    finally:
        # restore import
        builtins.__import__ = orig_import


def test_ensure_client_client_exception_round_118():
    """If google.genai.Client raises during construction, _ensure_client logs an error and re-raises the exception."""
    m = importlib.import_module("gpt_researcher.llm_provider.image.image_generator")
    ImageGeneratorProvider = m.ImageGeneratorProvider

    class BadClient:
        def __init__(self, api_key):
            raise RuntimeError("boom")

    # install fake google.genai whose Client raises
    _make_fake_google(BadClient)

    # capture logger.error calls
    mock_logger = mock.Mock()
    m.logger = mock_logger

    try:
        provider = ImageGeneratorProvider("bad-model", "bad-key", output_dir=".")
        provider._client = None
        provider.api_key = "bad-key"

        with pytest.raises(RuntimeError) as excinfo:
            provider._ensure_client()

        # logger.error should have been called with a message including the failure prefix
        mock_logger.error.assert_called()
        err_msg = mock_logger.error.call_args[0][0]
        assert "Failed to initialize image generation client" in err_msg

        # original exception message should be part of the logged text
        assert "boom" in err_msg
    finally:
        _cleanup_fake_google()
