# file: openhands/core/config/utils.py:144-373
# asked: {"lines": [191, 193, 197, 198, 207, 208, 209, 218, 219, 220, 231, 232, 239, 240, 241, 244, 245, 246, 247, 251, 252, 253, 254, 255, 256, 259, 260, 262, 263, 264, 275, 276, 289, 290, 291, 293, 295, 299, 300, 301, 303, 304, 305, 306, 307, 325, 326, 327, 353, 354, 355, 373], "branches": [[181, 197], [186, 195], [190, 191], [192, 193], [228, 238], [238, 239], [244, 245], [244, 268], [252, 253], [252, 255], [253, 252], [253, 254], [272, 283], [287, 298], [298, 299], [303, 304], [303, 311], [318, 350], [372, 373]]}
# gained: {"lines": [191, 193, 197, 198, 207, 208, 209, 239, 240, 241, 244, 245, 246, 247, 251, 252, 253, 254, 255, 256, 259, 260, 289, 293, 295, 299, 300, 301, 303, 304, 305, 306, 307, 373], "branches": [[181, 197], [190, 191], [192, 193], [238, 239], [244, 245], [252, 253], [252, 255], [253, 252], [253, 254], [298, 299], [303, 304], [372, 373]]}

import sys
import types
import toml
import pytest
from pydantic import SecretStr, ValidationError

from openhands.core.config import utils as utils_module


class DummyAgentConfig:
    def __init__(self):
        self.model_routing = None
        self.condenser = None


class DummyCfg:
    # type hints to be used by get_type_hints in load_from_toml
    some_secret: SecretStr
    union_secret: SecretStr | str

    def __init__(self):
        # ensure attributes exist so hasattr(cfg, key) returns True
        self.some_secret = None
        self.union_secret = None

        self.enable_default_condenser = False
        self.llms = {}
        self._agents = {}
        self.security = None
        self.sandbox = None
        self.mcp = None
        self.kubernetes = None
        self.extended = None
        self._default_agent = DummyAgentConfig()

    def set_agent_config(self, conf, key):
        self._agents[key] = conf

    def set_llm_config(self, conf, key):
        self.llms[key] = conf

    def get_agent_config(self):
        return self._default_agent

    def get_llm_config(self):
        # return any llm config as default
        return next(iter(self.llms.values())) if self.llms else None


class SimpleLLM:
    def __init__(self, for_routing=False):
        self.for_routing = for_routing


class SimpleModelRouting:
    def __init__(self):
        self.llms_for_routing = {}


# Test 1: core secret conversion (both SecretStr and UnionType branch) and unknown key
def test_core_secret_and_unknown_key(tmp_path, monkeypatch):
    cfg = DummyCfg()
    toml_data = {
        "core": {
            "some_secret": "plainsecret",
            "union_secret": "anothersecret",
            "unknown_key": "should_warn",
        }
    }
    p = tmp_path / "core.toml"
    p.write_text(toml.dumps(toml_data), encoding="utf-8")

    # Run loader
    utils_module.load_from_toml(cfg, str(p))

    # Assert secret conversions happened
    assert isinstance(cfg.some_secret, SecretStr)
    assert cfg.some_secret.get_secret_value() == "plainsecret"
    assert isinstance(cfg.union_secret, SecretStr)
    assert cfg.union_secret.get_secret_value() == "anothersecret"
    # unknown_key should not be set as attribute on cfg
    assert not hasattr(cfg, "unknown_key")


# Test 2: full successful parsing for all sections that assign values
def test_all_sections_successful(tmp_path, monkeypatch):
    cfg = DummyCfg()

    # Prepare TOML with all relevant sections
    toml_data = {
        "agent": {"a": "x"},
        "llm": {"l1": {"dummy": True}},
        "security": {"security": {"ok": True}},
        "model_routing": {"mr": {"dummy": True}},
        "sandbox": {"sandbox": {"ok": True}},
        "mcp": {"mcp": {"ok": True}},
        "kubernetes": {"kubernetes": {"ok": True}},
        "condenser": {"condenser": {"ok": True}},
        "extended": {"some": "val"},
        "weirdSection": {"o": 1},  # unknown section to trigger warning at end
    }
    p = tmp_path / "full.toml"
    p.write_text(toml.dumps(toml_data), encoding="utf-8")

    # Monkeypatch AgentConfig.from_toml_section to return mapping that set_agent_config can accept
    class FakeAgentConfig:
        @staticmethod
        def from_toml_section(section):
            return {"default": {"agent": "cfg"}}

    monkeypatch.setattr(utils_module, "AgentConfig", FakeAgentConfig)

    # Monkeypatch LLMConfig to return llm mapping; set one with for_routing True
    class FakeLLMConfig:
        @staticmethod
        def from_toml_section(section):
            return {
                "llm_for_route": SimpleLLM(for_routing=True),
                "llm_not_route": SimpleLLM(for_routing=False),
            }

    monkeypatch.setattr(utils_module, "LLMConfig", FakeLLMConfig)

    # Monkeypatch SecurityConfig
    class FakeSecurityConfig:
        @staticmethod
        def from_toml_section(section):
            return {"security": "SECURED"}

    monkeypatch.setattr(utils_module, "SecurityConfig", FakeSecurityConfig)

    # Monkeypatch ModelRoutingConfig
    class FakeModelRoutingConfig:
        @staticmethod
        def from_toml_section(section):
            return {"model_routing": SimpleModelRouting()}

    monkeypatch.setattr(utils_module, "ModelRoutingConfig", FakeModelRoutingConfig)

    # Monkeypatch SandboxConfig
    class FakeSandboxConfig:
        @staticmethod
        def from_toml_section(section):
            return {"sandbox": "SANDBOXED"}

    monkeypatch.setattr(utils_module, "SandboxConfig", FakeSandboxConfig)

    # Monkeypatch MCPConfig
    class FakeMCPConfig:
        @staticmethod
        def from_toml_section(section):
            return {"mcp": "MCP_OK"}

    monkeypatch.setattr(utils_module, "MCPConfig", FakeMCPConfig)

    # Monkeypatch KubernetesConfig
    class FakeKubeConfig:
        @staticmethod
        def from_toml_section(section):
            return {"kubernetes": "KUBE_OK"}

    monkeypatch.setattr(utils_module, "KubernetesConfig", FakeKubeConfig)

    # Monkeypatch condenser_config_from_toml_section
    def fake_condenser_from_toml(section, llms):
        return {"condenser": "CONDENSER_OK"}

    monkeypatch.setattr(utils_module, "condenser_config_from_toml_section", fake_condenser_from_toml)

    # Monkeypatch ExtendedConfig constructor
    class FakeExtended:
        def __init__(self, section):
            self.data = section

    monkeypatch.setattr(utils_module, "ExtendedConfig", FakeExtended)

    # Run loader
    utils_module.load_from_toml(cfg, str(p))

    # Assertions that values were applied
    # Agent set via set_agent_config (the FakeAgentConfig returns mapping, so check _agents updated)
    assert "default" in cfg._agents
    # LLMs set
    assert "llm_for_route" in cfg.llms and "llm_not_route" in cfg.llms
    # Security assigned
    assert cfg.security == "SECURED"
    # Model routing assigned to default agent
    assert cfg.get_agent_config().model_routing is not None
    # llms_for_routing should include only the for_routing one
    assert "llm_for_route" in cfg.get_agent_config().model_routing.llms_for_routing
    assert "llm_not_route" not in cfg.get_agent_config().model_routing.llms_for_routing
    # Sandbox/mcp/kubernetes assigned
    assert cfg.sandbox == "SANDBOXED"
    assert cfg.mcp == "MCP_OK"
    assert cfg.kubernetes == "KUBE_OK"
    # Condenser assigned to default agent
    assert cfg.get_agent_config().condenser == "CONDENSER_OK"
    # Extended set
    assert isinstance(cfg.extended, FakeExtended)
    assert cfg.extended.data == toml_data["extended"]


# Test 3: error handling branches for sections that re-raise ValueError and those that log warnings
def test_error_cases_raise_and_warnings(tmp_path, monkeypatch):
    # Prepare TOML files for various failing sections
    # 1) Security raises ValueError -> should re-raise new ValueError
    cfg1 = DummyCfg()
    toml_security = {"security": {"some": "x"}}
    p1 = tmp_path / "sec.toml"
    p1.write_text(toml.dumps(toml_security), encoding="utf-8")

    class BadSecurity:
        @staticmethod
        def from_toml_section(section):
            raise ValueError("bad security")

    monkeypatch.setattr(utils_module, "SecurityConfig", BadSecurity)
    with pytest.raises(ValueError) as ei:
        utils_module.load_from_toml(cfg1, str(p1))
    assert "Error in [security] section in config.toml" in str(ei.value)

    # 2) Sandbox raises ValueError -> should be re-raised wrapped
    cfg2 = DummyCfg()
    toml_sandbox = {"sandbox": {"some": "x"}}
    p2 = tmp_path / "sandbox.toml"
    p2.write_text(toml.dumps(toml_sandbox), encoding="utf-8")

    class BadSandbox:
        @staticmethod
        def from_toml_section(section):
            raise ValueError("bad sandbox")

    monkeypatch.setattr(utils_module, "SandboxConfig", BadSandbox)
    with pytest.raises(ValueError) as ei2:
        utils_module.load_from_toml(cfg2, str(p2))
    assert "Error in [sandbox] section in config.toml" in str(ei2.value)

    # 3) MCP raises ValueError -> should be re-raised wrapped
    cfg3 = DummyCfg()
    toml_mcp = {"mcp": {"some": "x"}}
    p3 = tmp_path / "mcp.toml"
    p3.write_text(toml.dumps(toml_mcp), encoding="utf-8")

    class BadMCP:
        @staticmethod
        def from_toml_section(section):
            raise ValueError("bad mcp")

    monkeypatch.setattr(utils_module, "MCPConfig", BadMCP)
    with pytest.raises(ValueError) as ei3:
        utils_module.load_from_toml(cfg3, str(p3))
    assert "Error in MCP sections in config.toml" in str(ei3.value)

    # 4) AgentConfig.from_toml_section raises ValidationError -> should be caught and not raise
    cfg4 = DummyCfg()
    toml_agent = {"agent": {"a": "b"}}
    p4 = tmp_path / "agent.toml"
    p4.write_text(toml.dumps(toml_agent), encoding="utf-8")

    class BadAgent:
        @staticmethod
        def from_toml_section(section):
            # create a minimal ValidationError; pydantic requires at least one error dict
            raise ValidationError([{"loc": ("x",), "msg": "err", "type": "value_error"}], model=object)

    monkeypatch.setattr(utils_module, "AgentConfig", BadAgent)
    # Should not raise, only log; ensure no agents set
    utils_module.load_from_toml(cfg4, str(p4))
    assert cfg4._agents == {}

    # 5) Kubernetes from_toml_section raises TypeError -> should be caught and not raise
    cfg5 = DummyCfg()
    toml_kube = {"kubernetes": {"k": 1}}
    p5 = tmp_path / "kube.toml"
    p5.write_text(toml.dumps(toml_kube), encoding="utf-8")

    class BadKube:
        @staticmethod
        def from_toml_section(section):
            raise TypeError("bad kube")

    monkeypatch.setattr(utils_module, "KubernetesConfig", BadKube)
    # Should not raise, only log
    utils_module.load_from_toml(cfg5, str(p5))
    assert cfg5.kubernetes is None


# Test 4: condenser absent -> default LLMSummarizingCondenserConfig assignment when enable_default_condenser True
def test_default_condenser_assignment_when_no_condenser_section(tmp_path, monkeypatch):
    cfg = DummyCfg()
    cfg.enable_default_condenser = True

    # Provide a default llm config so LLMSummarizingCondenserConfig can use it
    cfg.set_llm_config(SimpleLLM(for_routing=False), "default_llm")

    toml_data = {
        # No 'condenser' section here
        "llm": {"default_llm": {"dummy": True}},
    }
    p = tmp_path / "nocondenser.toml"
    p.write_text(toml.dumps(toml_data), encoding="utf-8")

    # Create a fake module for openhands.core.config.condenser_config with LLMSummarizingCondenserConfig
    mod_name = "openhands.core.config.condenser_config"
    fake_mod = types.ModuleType(mod_name)

    class LLMSummarizingCondenserConfig:
        def __init__(self, llm_config=None, type=None):
            self.llm_config = llm_config
            self.type = type

    fake_mod.LLMSummarizingCondenserConfig = LLMSummarizingCondenserConfig

    # Ensure import inside function finds our fake module
    monkeypatch.setitem(sys.modules, mod_name, fake_mod)

    # Also monkeypatch LLMConfig.from_toml_section to set llm in cfg.llms
    class FakeLLMConfig2:
        @staticmethod
        def from_toml_section(section):
            return {"default_llm": SimpleLLM(for_routing=False)}

    monkeypatch.setattr(utils_module, "LLMConfig", FakeLLMConfig2)

    # Run loader
    utils_module.load_from_toml(cfg, str(p))

    # Default condenser should be assigned and be instance of our fake LLMSummarizingCondenserConfig
    default_agent = cfg.get_agent_config()
    assert isinstance(default_agent.condenser, LLMSummarizingCondenserConfig)
    assert default_agent.condenser.type == "llm"
    # llm_config on condenser should equal cfg.get_llm_config()
    assert default_agent.condenser.llm_config is cfg.get_llm_config()
