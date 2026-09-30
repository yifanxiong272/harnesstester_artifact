import sys
import types
from types import SimpleNamespace
import importlib
import aider.commands as commands


class FakeIO:
    def __init__(self):
        # record tuples of (kind, message) in order
        self.calls = []

    def tool_output(self, msg):
        self.calls.append(("output", msg))

    def tool_error(self, msg):
        self.calls.append(("error", msg))


def _make_coders_module(pairs):
    """Create a fake 'aider.coders' module where pairs is a list of
    (edit_format, docstring) tuples used to populate __all__.
    """
    mod = types.ModuleType("aider.coders")
    all_list = []
    for fmt, doc in pairs:
        # Use a SimpleNamespace so it has attributes edit_format and __doc__
        obj = SimpleNamespace(edit_format=fmt)
        # assign __doc__ attribute explicitly
        obj.__doc__ = doc
        all_list.append(obj)
    mod.__all__ = all_list
    return mod


def _make_commands_instance(io=None, main_model_format="main_fmt"):
    # Create a bare Commands instance without running __init__
    inst = commands.Commands.__new__(commands.Commands)
    inst.io = io or FakeIO()
    # minimal coder object with main_model.edit_format attribute
    inst.coder = SimpleNamespace(main_model=SimpleNamespace(edit_format=main_model_format))
    return inst


def _install_coders_into_aider(coders_mod):
    # Ensure the aider package object exists and patch its 'coders' attribute and sys.modules entry
    import aider as aider_pkg
    # attach the fake coders module to the aider package so 'from aider import coders' picks it up
    setattr(aider_pkg, "coders", coders_mod)
    sys.modules["aider.coders"] = coders_mod


def test_unknown_nonempty_round_028():
    # Setup fake coders with one format that overlaps show_formats (ask)
    # and one custom format that should be shown in the "valid formats" list.
    coders_mod = _make_coders_module([
        ("custom", "Custom format description."),
        ("ask", "Ask questions without making edits."),
    ])
    _install_coders_into_aider(coders_mod)

    io = FakeIO()
    inst = _make_commands_instance(io=io)

    # call with an unknown non-empty ef -> should call tool_error then list formats
    inst.cmd_chat_mode("unknown")

    assert io.calls, "Expected io to have recorded calls"
    # first call must be an error mentioning the unknown mode with trailing newline
    assert io.calls[0] == (
        "error",
        'Chat mode "unknown" should be one of these:\n',
    )

    # subsequent outputs should include the show_formats entries (help/ask/code/...)
    outputs = [m for kind, m in io.calls[1:]]
    joined = "\n".join(outputs)
    assert "- help" in joined, "show_formats should include help"
    assert "- ask" in joined, "show_formats should include ask"
    assert "- code" in joined, "show_formats should include code"

    # There should be a separator line for valid edit formats
    assert "Or a valid edit format" in joined

    # Our custom valid format should be present and not duplicated with show_formats
    assert any(line.strip().startswith("- custom") for line in outputs), "custom format must be printed"


def test_empty_arg_round_028():
    # When args is empty/whitespace, the function should use tool_output (not tool_error)
    coders_mod = _make_coders_module([("custom", "Custom."), ("ask", "Ask.")])
    _install_coders_into_aider(coders_mod)

    io = FakeIO()
    inst = _make_commands_instance(io=io)

    inst.cmd_chat_mode("   ")  # whitespace -> ef == ''

    assert io.calls, "Expected some io calls"
    # first call must be an output informing valid choices (no error)
    assert io.calls[0] == (
        "output",
        "Chat mode should be one of these:\n",
    )

    # ensure show_formats printed as outputs after that
    outputs = [m for kind, m in io.calls[1:]]
    assert any("- help" in o for o in outputs)
    assert any("- custom" in o for o in outputs)


def test_switch_to_code_round_028():
    # When ef == 'code', Commands should raise SwitchCoder with edit_format taken
    # from self.coder.main_model.edit_format and summarize_from_coder False.
    coders_mod = _make_coders_module([("custom", "Custom."), ("ask", "Ask.")])
    _install_coders_into_aider(coders_mod)

    io = FakeIO()
    inst = _make_commands_instance(io=io, main_model_format="main_from_main_model")

    try:
        inst.cmd_chat_mode("code")
        raised = None
    except commands.SwitchCoder as exc:
        raised = exc

    assert raised is not None, "SwitchCoder must be raised for 'code'"
    assert getattr(raised, "edit_format") == "main_from_main_model"
    assert getattr(raised, "summarize_from_coder") is False


def test_switch_to_valid_format_round_028():
    # When ef equals a valid edit_format provided by coders.__all__, SwitchCoder is raised
    coders_mod = _make_coders_module([("custom", "Custom desc."), ("ask", "Ask.")])
    _install_coders_into_aider(coders_mod)

    io = FakeIO()
    inst = _make_commands_instance(io=io, main_model_format="unused_main")

    try:
        inst.cmd_chat_mode("custom")
        raised = None
    except commands.SwitchCoder as exc:
        raised = exc

    assert raised is not None, "SwitchCoder must be raised for a valid custom format"
    assert getattr(raised, "edit_format") == "custom"
    # For non-'code' and non-'ask' formats summarize_from_coder remains True
    assert getattr(raised, "summarize_from_coder") is True


def test_switch_to_ask_round_028():
    # When ef == 'ask', summarize_from_coder should be False, and edit_format == 'ask'
    coders_mod = _make_coders_module([("custom", "Custom."), ("ask", "Ask description.")])
    _install_coders_into_aider(coders_mod)

    io = FakeIO()
    inst = _make_commands_instance(io=io, main_model_format="ignored")

    try:
        inst.cmd_chat_mode("ask")
        raised = None
    except commands.SwitchCoder as exc:
        raised = exc

    assert raised is not None
    assert getattr(raised, "edit_format") == "ask"
    assert getattr(raised, "summarize_from_coder") is False
