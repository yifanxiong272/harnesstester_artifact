import logging
import pytest
from gpt_researcher.llm_provider.image.image_generator import ImageGeneratorProvider


def test_is_available_no_api_key_round_136(monkeypatch):
    # Ensure environment keys are absent so __init__ won't pick them up
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    provider = ImageGeneratorProvider(api_key=None)
    # Sanity: api_key should be None after construction
    assert provider.api_key is None

    # When no api key is present, is_available must return False and must not attempt client init
    assert provider.is_available() is False


def test_is_available_with_api_key_success_round_136(monkeypatch):
    # Provide a deterministic api_key so the code takes the successful branch
    provider = ImageGeneratorProvider(api_key="valid-key")

    # Patch _ensure_client to a deterministic, side-effectful no-op that sets _client
    def fake_ensure(self):
        # Simulate successful client initialization
        self._client = "fake-client"

    monkeypatch.setattr(ImageGeneratorProvider, "_ensure_client", fake_ensure)

    # Now is_available should return True and the fake client should be set
    assert provider.is_available() is True
    assert getattr(provider, "_client") == "fake-client"


def test_is_available_with_api_key_client_init_failure_round_136(monkeypatch, caplog):
    # Provide api_key so the method attempts client initialization
    provider = ImageGeneratorProvider(api_key="valid-key")

    # Patch _ensure_client to deterministically raise an exception
    def raise_ensure(self):
        raise RuntimeError("init failed")

    monkeypatch.setattr(ImageGeneratorProvider, "_ensure_client", raise_ensure)

    # Capture warnings emitted by is_available on failure
    caplog.set_level(logging.WARNING)

    result = provider.is_available()
    assert result is False

    # The warning message should include the exception text
    assert any(
        "Image generation not available: init failed" in rec.getMessage()
        for rec in caplog.records
    )
