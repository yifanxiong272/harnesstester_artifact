import importlib
import types
import pytest

# deterministic, pure-Python dummy classes to stand in for real configs and models
class SimpleConfig:
    def __init__(self, **kwargs):
        # accept arbitrary fields like pydantic would
        for k, v in kwargs.items():
            setattr(self, k, v)

class GenericDummyConfig(SimpleConfig):
    def model_dump(self):
        # return a plain dict suitable for the target specific-config constructors
        # include the name field if available
        d = {k: v for k, v in self.__dict__.items()}
        return d

class DummyModel:
    def __init__(self, cfg, tools):
        # record what was passed for assertions
        self._cfg = cfg
        self._tools = tools


def _patch_all(module, *, generic_cls=None, human_cfg=None, human_thought_cfg=None, replay_cfg=None, instant_cfg=None,
               human_model=None, human_thought_model=None, replay_model=None, instant_model=None, lite_model=None):
    # monkeypatch the module symbols by direct assignment
    if generic_cls is not None:
        setattr(module, "GenericAPIModelConfig", generic_cls)
    if human_cfg is not None:
        setattr(module, "HumanModelConfig", human_cfg)
    if human_thought_cfg is not None:
        setattr(module, "HumanThoughtModelConfig", human_thought_cfg)
    if replay_cfg is not None:
        setattr(module, "ReplayModelConfig", replay_cfg)
    if instant_cfg is not None:
        setattr(module, "InstantEmptySubmitModelConfig", instant_cfg)

    if human_model is not None:
        setattr(module, "HumanModel", human_model)
    if human_thought_model is not None:
        setattr(module, "HumanThoughtModel", human_thought_model)
    if replay_model is not None:
        setattr(module, "ReplayModel", replay_model)
    if instant_model is not None:
        setattr(module, "InstantEmptySubmitTestModel", instant_model)
    if lite_model is not None:
        setattr(module, "LiteLLMModel", lite_model)


@pytest.fixture(autouse=True)
def reload_models_module():
    """Import fresh module for each test to avoid cross-test pollution."""
    # ensure we get the real module object to patch attributes on
    module = importlib.import_module("sweagent.agent.models")
    yield module


def test_get_model_generic_human_round_046(reload_models_module):
    module = reload_models_module

    # Prepare dummy config & model classes and patch into module
    Generic = GenericDummyConfig
    HumanCfg = type("HumanCfg", (SimpleConfig,), {})
    Dummy = DummyModel

    _patch_all(module,
               generic_cls=Generic,
               human_cfg=HumanCfg,
               human_model=Dummy,
               human_thought_cfg=type("HTCfg", (SimpleConfig,), {}),
               replay_cfg=type("RCfg", (SimpleConfig,), {}),
               instant_cfg=type("ICfg", (SimpleConfig,), {}),
               human_thought_model=Dummy,
               replay_model=Dummy,
               instant_model=Dummy,
               lite_model=Dummy)

    # Create a GenericAPIModelConfig-like instance whose name triggers the conversion
    args = Generic(name="human", extra_field=123)

    res = module.get_model(args, tools={"t": "v"})

    # It should have converted Generic->HumanModelConfig and then constructed HumanModel
    assert isinstance(res, Dummy)
    # The model was given a config that should be an instance of the patched HumanModelConfig
    assert isinstance(res._cfg, HumanCfg)
    assert getattr(res._cfg, "name") == "human"
    # tools passed through
    assert res._tools == {"t": "v"}


def test_get_model_specific_human_thought_round_046(reload_models_module):
    module = reload_models_module

    # Patch the module so that HumanThoughtModelConfig and implementation are simple
    HumanThoughtCfg = type("HumanThoughtCfg", (SimpleConfig,), {})
    Dummy = DummyModel

    _patch_all(module,
               generic_cls=GenericDummyConfig,
               human_cfg=type("HumanCfg2", (SimpleConfig,), {}),
               human_thought_cfg=HumanThoughtCfg,
               human_model=Dummy,
               human_thought_model=Dummy,
               replay_model=Dummy,
               instant_model=Dummy,
               lite_model=Dummy)

    # Create an instance of the specific HumanThoughtModelConfig (no conversion path)
    args = HumanThoughtCfg(name="human_thought", note="X")

    res = module.get_model(args, tools=None)

    assert isinstance(res, Dummy)
    # The model should have received the same config instance type
    assert isinstance(res._cfg, HumanThoughtCfg)
    assert getattr(res._cfg, "name") == "human_thought"


def test_get_model_generic_replay_round_046(reload_models_module):
    module = reload_models_module

    # Patch config and model classes so conversion for 'replay' works
    Generic = GenericDummyConfig
    ReplayCfg = type("ReplayCfg", (SimpleConfig,), {})
    Dummy = DummyModel

    _patch_all(module,
               generic_cls=Generic,
               human_cfg=type("HCfg", (SimpleConfig,), {}),
               human_thought_cfg=type("HTCfg2", (SimpleConfig,), {}),
               replay_cfg=ReplayCfg,
               instant_cfg=type("ICfg2", (SimpleConfig,), {}),
               human_model=Dummy,
               human_thought_model=Dummy,
               replay_model=Dummy,
               instant_model=Dummy,
               lite_model=Dummy)

    args = Generic(name="replay", replay_seq=[1, 2, 3])

    res = module.get_model(args, tools={})

    assert isinstance(res, Dummy)
    assert isinstance(res._cfg, ReplayCfg)
    assert getattr(res._cfg, "name") == "replay"
    # conversion should have preserved other fields
    assert getattr(res._cfg, "replay_seq") == [1, 2, 3]


def test_get_model_fallback_litellm_round_046(reload_models_module):
    module = reload_models_module

    # Patch to ensure the final fallback to LiteLLMModel is observable and safe
    Generic = GenericDummyConfig
    DummyLite = DummyModel

    _patch_all(module,
               generic_cls=Generic,
               human_cfg=type("HCfg3", (SimpleConfig,), {}),
               human_thought_cfg=type("HTCfg3", (SimpleConfig,), {}),
               replay_cfg=type("RCfg3", (SimpleConfig,), {}),
               instant_cfg=type("ICfg3", (SimpleConfig,), {}),
               human_model=DummyModel,
               human_thought_model=DummyModel,
               replay_model=DummyModel,
               instant_model=DummyModel,
               lite_model=DummyLite)

    # A GenericAPIModelConfig whose name does not match any of the specific handled names
    args = Generic(name="something_else", foo="bar")

    res = module.get_model(args, tools=None)

    # Should return an instance of the patched LiteLLMModel
    assert isinstance(res, DummyLite)
    # And should have received the original Generic-config instance
    assert isinstance(res._cfg, Generic)
    assert getattr(res._cfg, "name") == "something_else"
