# file: gpt_researcher/skills/image_generator.py:48-67
# asked: {"lines": [54, 55, 56, 57, 59, 60, 61, 62, 64, 65, 66, 67], "branches": [[52, 54], [56, 57], [56, 59], [60, 61], [60, 64]]}
# gained: {"lines": [54, 55, 56, 57, 59, 60, 61, 62, 64, 65, 66, 67], "branches": [[52, 54], [56, 57], [56, 59], [60, 61], [60, 64]]}

import importlib
import types
import pytest


@pytest.fixture
def img_mod():
    # Import the module under test
    return importlib.import_module("gpt_researcher.skills.image_generator")


def make_cfg(**kwargs):
    return types.SimpleNamespace(**kwargs)


def test_modelslab_provider_available_sets_image_provider(monkeypatch, img_mod):
    # Arrange: cfg enabled and provider 'modelslab'
    cfg = make_cfg(IMAGE_GENERATION_ENABLED=True, IMAGE_GENERATION_PROVIDER="modelslab", IMAGE_GENERATION_MODEL="m-123")

    # Fake ModelsLabImageGeneratorProvider that records model_id and reports available
    class FakeModelsLab:
        def __init__(self, model_id=None):
            self.model_id = model_id

        def is_available(self):
            return True

    # Patch the provider in the module
    monkeypatch.setattr(img_mod, "ModelsLabImageGeneratorProvider", FakeModelsLab)

    # Create a lightweight instance to bind to the real method
    inst = types.SimpleNamespace(cfg=cfg)

    # Act
    img_mod.ImageGenerator._init_provider(inst)

    # Assert: image_provider set and is instance of our fake, model_id preserved
    assert hasattr(inst, "image_provider"), "image_provider should be set when provider is available"
    assert isinstance(inst.image_provider, FakeModelsLab)
    assert inst.image_provider.model_id == "m-123"


def test_imagegenerator_provider_not_available_does_not_set_image_provider(monkeypatch, img_mod):
    # Arrange: enabled True, default provider (google)
    cfg = make_cfg(IMAGE_GENERATION_ENABLED=True, IMAGE_GENERATION_PROVIDER="google", IMAGE_GENERATION_MODEL="gpt-img")

    # Fake ImageGeneratorProvider that is not available
    class FakeImageGen:
        def __init__(self, model_name=None):
            self.model_name = model_name

        def is_available(self):
            return False

    monkeypatch.setattr(img_mod, "ImageGeneratorProvider", FakeImageGen)

    inst = types.SimpleNamespace(cfg=cfg)

    # Act
    img_mod.ImageGenerator._init_provider(inst)

    # Assert: image_provider should NOT be set when provider reports not available
    assert not hasattr(inst, "image_provider"), "image_provider should not be set if provider.is_available() is False"


def test_provider_construction_raises_results_in_image_provider_none(monkeypatch, img_mod):
    # Arrange: enabled True, default provider (google)
    cfg = make_cfg(IMAGE_GENERATION_ENABLED=True, IMAGE_GENERATION_PROVIDER="google", IMAGE_GENERATION_MODEL="mymodel")

    # Fake ImageGeneratorProvider whose constructor raises to trigger the exception handling path
    class RaisingProvider:
        def __init__(self, model_name=None):
            raise RuntimeError("constructor failure")

    monkeypatch.setattr(img_mod, "ImageGeneratorProvider", RaisingProvider)

    inst = types.SimpleNamespace(cfg=cfg)

    # Act
    img_mod.ImageGenerator._init_provider(inst)

    # Assert: exception branch should set image_provider to None
    assert hasattr(inst, "image_provider")
    assert inst.image_provider is None
