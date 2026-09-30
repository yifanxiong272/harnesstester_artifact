import importlib

import pytest

# Load the module under test
ig = importlib.import_module('gpt_researcher.skills.image_generator')


class DummyCfg:
    def __init__(self, enabled=None, provider=None, model=None):
        if enabled is not None:
            self.IMAGE_GENERATION_ENABLED = enabled
        if provider is not None:
            self.IMAGE_GENERATION_PROVIDER = provider
        if model is not None:
            self.IMAGE_GENERATION_MODEL = model


class DummySelf:
    def __init__(self, cfg, initial_image_provider=None):
        self.cfg = cfg
        # Set an initial sentinel value to detect changes
        self.image_provider = initial_image_provider


class FakeLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []
        self.errors = []

    def info(self, msg):
        self.infos.append(msg)

    def warning(self, msg):
        self.warnings.append(msg)

    def error(self, msg):
        self.errors.append(msg)


def test_disabled_round_081():
    """If IMAGE_GENERATION_ENABLED is False, _init_provider should return early and not modify image_provider."""
    cfg = DummyCfg(enabled=False)
    dummy = DummySelf(cfg, initial_image_provider='SENTINEL')

    # Call the bound function directly with our dummy self
    ig.ImageGenerator._init_provider(dummy)

    # Should not have changed
    assert dummy.image_provider == 'SENTINEL'


def test_modelslab_available_round_081(monkeypatch):
    """When provider_name is 'modelslab' and provider.is_available() is True, image_provider is set."""
    cfg = DummyCfg(enabled=True, provider='modelslab', model='m-123')
    dummy = DummySelf(cfg, initial_image_provider=None)

    # Fake ModelsLabImageGeneratorProvider used by the module
    class FakeModelsLab:
        def __init__(self, model_id=None):
            self.model_id = model_id

        def is_available(self):
            return True

    fake_logger = FakeLogger()

    monkeypatch.setattr(ig, 'ModelsLabImageGeneratorProvider', FakeModelsLab)
    monkeypatch.setattr(ig, 'logger', fake_logger)

    ig.ImageGenerator._init_provider(dummy)

    # image_provider should be set to an instance of our fake provider
    assert isinstance(dummy.image_provider, FakeModelsLab)
    assert dummy.image_provider.model_id == 'm-123'

    # Should have logged an info message mentioning provider name
    assert any('modelslab' in msg for msg in fake_logger.infos)


def test_default_provider_unavailable_round_081(monkeypatch):
    """When default provider (not 'modelslab') is selected but is_available() is False, image_provider remains None and a warning is logged."""
    # Do not set provider so getattr will use default 'google'
    cfg = DummyCfg(enabled=True, provider=None, model='g-model')
    # Intentionally do not set IMAGE_GENERATION_PROVIDER to force default path
    # Use object without provider attribute to exercise getattr default
    cfg_missing_provider = DummyCfg(enabled=True, model='g-model')
    dummy = DummySelf(cfg_missing_provider, initial_image_provider=None)

    class FakeDefaultProvider:
        def __init__(self, model_name=None):
            self.model_name = model_name

        def is_available(self):
            return False

    fake_logger = FakeLogger()

    monkeypatch.setattr(ig, 'ImageGeneratorProvider', FakeDefaultProvider)
    monkeypatch.setattr(ig, 'logger', fake_logger)

    ig.ImageGenerator._init_provider(dummy)

    # Provider should not be set because is_available returned False
    assert dummy.image_provider is None

    # A warning should have been emitted and mention the default provider name ('google')
    assert any("google" in w for w in fake_logger.warnings)


def test_constructor_exception_sets_none_round_081(monkeypatch):
    """If provider constructor raises, the exception is caught and image_provider is set to None and error logged."""
    cfg = DummyCfg(enabled=True, provider='modelslab', model='bad-model')
    dummy = DummySelf(cfg, initial_image_provider='WAS_SET')

    # Make the constructor raise to trigger the except clause
    def raising_constructor(*args, **kwargs):
        raise RuntimeError('construction failed')

    fake_logger = FakeLogger()

    monkeypatch.setattr(ig, 'ModelsLabImageGeneratorProvider', raising_constructor)
    monkeypatch.setattr(ig, 'logger', fake_logger)

    ig.ImageGenerator._init_provider(dummy)

    # image_provider must be set to None by the exception handler
    assert dummy.image_provider is None

    # An error must have been logged with the exception message
    assert any('construction failed' in e for e in fake_logger.errors)
