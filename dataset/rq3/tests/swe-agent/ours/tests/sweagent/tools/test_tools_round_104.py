import pytest
from types import SimpleNamespace
from importlib import import_module

# Deterministic tests for ToolConfig.model_post_init (round 104)

def test_error_when_disable_bash_and_bad_parser_round_104(monkeypatch):
    """If enable_bash_tool is False and the parser is not an allowed parser,
    model_post_init should raise ValueError with a message that references
    the parser 'type' class attributes. We patch the parser classes to ensure
    those class attributes exist.
    """
    tools_mod = import_module("sweagent.tools.tools")
    ToolConfig = tools_mod.ToolConfig

    # Provide simple stand-ins for the parser classes that expose class-level `type`
    monkeypatch.setattr(tools_mod, "FunctionCallingParser", type("FCP", (), {"type": "function_calling"}))
    monkeypatch.setattr(tools_mod, "JsonParser", type("JP", (), {"type": "json"}))

    expected_msg = (
        f"Bash tool can only be disabled if {tools_mod.FunctionCallingParser.type} parser or "
        f"{tools_mod.JsonParser.type} parser is used."
    )

    # Use model_construct so construction triggers model_post_init deterministically
    with pytest.raises(ValueError) as excinfo:
        ToolConfig.model_construct(
            parse_function=SimpleNamespace(),
            enable_bash_tool=False,
            env_variables={},
            command_docs=None,
            format_error_template=None,
            submit_command="submit",
        )

    assert str(excinfo.value) == expected_msg


def test_success_when_function_calling_parser_round_104(monkeypatch):
    """When parse_function is a FunctionCallingParser-like instance and bash is disabled,
    model_post_init should complete and set multi_line_command_endings, command_docs,
    format_error_template, and submit_command_end_name.

    We monkeypatch the parser symbol to a small plain-Python class with a writable
    format_error_template, patch generate_command_docs, and patch ToolConfig.commands
    to return a deterministic submit command so the initialization can set submit_command_end_name.
    """
    tools_mod = import_module("sweagent.tools.tools")
    ToolConfig = tools_mod.ToolConfig

    # Fake parser exposing an instance attribute format_error_template and class attr type
    class FakeFunctionParser:
        type = "function_calling"
        def __init__(self):
            self.format_error_template = "PARSER_ERR_TEMPLATE"

    monkeypatch.setattr(tools_mod, "FunctionCallingParser", FakeFunctionParser)
    monkeypatch.setattr(tools_mod, "JsonParser", type("JP", (), {"type": "json"}))

    # Make generate_command_docs deterministic
    monkeypatch.setattr(tools_mod, "generate_command_docs", lambda commands, lst, **env: "GENERATED_DOCS")

    # Patch the commands property on ToolConfig to return a submit command object
    monkeypatch.setattr(
        tools_mod.ToolConfig,
        "commands",
        property(lambda self: [SimpleNamespace(name="submit", end_name="END_MARKER")]),
        raising=False,
    )

    cfg = ToolConfig.model_construct(
        parse_function=FakeFunctionParser(),
        enable_bash_tool=False,
        env_variables={"X": "1"},
        command_docs=None,
        format_error_template=None,
        submit_command="submit",
    )

    # Observable side effects asserted
    assert cfg.multi_line_command_endings == {"submit": "END_MARKER"}
    assert cfg.command_docs == "GENERATED_DOCS"
    assert cfg.format_error_template == "PARSER_ERR_TEMPLATE"
    assert cfg.submit_command_end_name == "END_MARKER"
