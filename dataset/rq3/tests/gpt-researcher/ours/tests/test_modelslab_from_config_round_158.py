from types import SimpleNamespace
import gpt_researcher.llm_provider.image.modelslab_image_generator as m

# Access the raw function object behind the @classmethod so we can supply a fake cls
from_config_func = m.ModelsLabImageGeneratorProvider.__dict__["from_config"].__func__

class FakeCls:
    """A lightweight stand-in for the real class used so tests do not depend on
    the real constructor or other side effects. It exposes DEFAULT_MODEL and
    records the model_id passed when instantiated.
    """
    DEFAULT_MODEL = "default-model-round158"

    def __init__(self, model_id=None, **kwargs):
        # mirror expected observable of the real class: retain model_id
        self.model_id = model_id


def test_from_config_disabled_round_158():
    """If IMAGE_GENERATION_ENABLED is False, from_config should return None."""
    cfg = SimpleNamespace(
        IMAGE_GENERATION_ENABLED=False,
        IMAGE_GENERATION_PROVIDER="modelslab",
        IMAGE_GENERATION_MODEL="irrelevant"
    )

    result = from_config_func(FakeCls, cfg)
    assert result is None


def test_from_config_wrong_provider_round_158():
    """If provider is not 'modelslab', from_config should return None even when enabled."""
    cfg = SimpleNamespace(
        IMAGE_GENERATION_ENABLED=True,
        IMAGE_GENERATION_PROVIDER="google",
        IMAGE_GENERATION_MODEL=None
    )

    result = from_config_func(FakeCls, cfg)
    assert result is None


def test_from_config_default_model_round_158():
    """When enabled and provider is 'modelslab' but no model provided, the
    returned instance should be constructed with DEFAULT_MODEL.
    """
    cfg = SimpleNamespace(
        IMAGE_GENERATION_ENABLED=True,
        IMAGE_GENERATION_PROVIDER="modelslab",
        IMAGE_GENERATION_MODEL=None
    )

    result = from_config_func(FakeCls, cfg)
    assert isinstance(result, FakeCls)
    assert result.model_id == FakeCls.DEFAULT_MODEL


def test_from_config_custom_model_round_158():
    """When enabled and provider is 'modelslab' and a model is provided, the
    returned instance should be constructed with that model id.
    """
    cfg = SimpleNamespace(
        IMAGE_GENERATION_ENABLED=True,
        IMAGE_GENERATION_PROVIDER="modelslab",
        IMAGE_GENERATION_MODEL="my-model-123"
    )

    result = from_config_func(FakeCls, cfg)
    assert isinstance(result, FakeCls)
    assert result.model_id == "my-model-123"
