def test_probe_001(monkeypatch):
    """Probe terminal-alias rewriting for duplicate-prefix handling.

    Activation: tool_name not in available_tools; TOOL_NAME_ALIASES maps base_name->'terminal';
    base_name is present in _TERMINAL_COMMAND_PREFIX_ALIASES; available_tools contains 'terminal';
    arguments['command'] already starts with base_name (e.g., 'git status').

    Invariant: normalization should not produce a duplicated leading token like 'git git status'.
    """

    # Import only the public module entrypoint and use its normalize_tool_call
    import openhands.sdk.agent.utils as utils

    # Deterministic inputs
    tool_name = "git"
    original_command = "git status"
    arguments = {"command": original_command, "summary": "no-op", "security_risk": False}
    available_tools = {"terminal"}

    # Ensure alias mapping is present and deterministic
    # TOOL_NAME_ALIASES is a module-level dict; update deterministically
    if not hasattr(utils, "TOOL_NAME_ALIASES") or utils.TOOL_NAME_ALIASES is None:
        monkeypatch.setattr(utils, "TOOL_NAME_ALIASES", {"git": "terminal"}, raising=False)
    else:
        # monkeypatch.setitem works for dict-like objects to avoid importing private symbols
        monkeypatch.setitem(utils.TOOL_NAME_ALIASES, "git", "terminal")

    # Ensure the terminal-prefix alias set contains our base token so the prefixing branch runs.
    # We patch the module attribute (private name) deterministically for the test harness.
    monkeypatch.setattr(utils, "_TERMINAL_COMMAND_PREFIX_ALIASES", {"git"}, raising=False)

    # Execute the public entrypoint
    normalized_name, normalized_args = utils.normalize_tool_call(tool_name, arguments, available_tools)

    # Primary oracle: canonical tool name and idempotent command (no duplicated prefix)
    assert normalized_name == "terminal", "expected normalization to map legacy alias to 'terminal'"
    assert "command" in normalized_args, "normalized arguments must include a 'command' entry"
    assert normalized_args["command"] == original_command, (
        f"expected command to be preserved when it already starts with base_name; got: {normalized_args['command']!r}"
    )
