# file: aider/commands.py:1109-1158
# asked: {"lines": [1113, 1114, 1122, 1123, 1148, 1149], "branches": [[1112, 1113], [1119, 1127], [1121, 1122], [1144, 1148]]}
# gained: {"lines": [1113, 1114, 1122, 1123, 1148, 1149], "branches": [[1112, 1113], [1121, 1122], [1144, 1148]]}

import pytest
import types

import aider.commands as commands_mod


def make_commands_instance():
    # Create a bare Commands instance with minimal required constructor args
    dummy_io = object()
    dummy_coder = types.SimpleNamespace()
    cmd = commands_mod.Commands(dummy_io, dummy_coder)
    return cmd


def test_cmd_help_empty_calls_basic_help_and_returns():
    cmd = make_commands_instance()
    called = {}

    def basic_help():
        called['was_called'] = True

    # attach basic_help to instance to override any existing method
    cmd.basic_help = basic_help

    # Call with only whitespace -> should call basic_help and return without error
    cmd.cmd_help("   ")
    assert called.get('was_called', False) is True


def test_cmd_help_install_help_extra_false_calls_tool_error_and_returns(monkeypatch):
    cmd = make_commands_instance()

    # coder should receive the 'interactive help' event before install_help_extra is called
    event_called = {}
    class DummyCoder:
        def event(self, name):
            event_called['name'] = name

    cmd.coder = DummyCoder()

    # io should expose tool_error that will be called when install_help_extra returns False
    io_called = {}
    class DummyIO:
        def tool_error(self, msg):
            io_called['msg'] = msg

    cmd.io = DummyIO()

    # Ensure cmd.help is falsy to trigger install_help_extra path
    cmd.help = None

    # Patch the install_help_extra used by aider.commands to return False
    monkeypatch.setattr(commands_mod, 'install_help_extra', lambda io: False)

    # Call with non-empty args so it proceeds down the function
    cmd.cmd_help("why does this happen?")

    assert event_called.get('name') == 'interactive help'
    assert io_called.get('msg') == "Unable to initialize interactive help."


def test_cmd_help_success_runs_and_raises_switchcoder_with_no_repo_map(monkeypatch):
    cmd = make_commands_instance()

    # coder must have event, get_announcements, edit_format, and repo_map attributes
    event_called = {}
    class DummyCoder:
        def __init__(self):
            self.edit_format = "the-format"
            self.repo_map = None  # triggers map_tokens=0, map_mul_no_files=1

        def event(self, name):
            event_called['name'] = name

        def get_announcements(self):
            return ["ANN1", "ANN2"]

    cmd.coder = DummyCoder()

    # Provide an io object (install_help_extra will receive it)
    class DummyIO:
        pass

    cmd.io = DummyIO()

    # Make help initially falsy so the install path is triggered
    cmd.help = None

    # Patch install_help_extra to return True so Help will be created
    monkeypatch.setattr(commands_mod, 'install_help_extra', lambda io: True)

    # Provide a Fake Help class with ask method
    class FakeHelp:
        def ask(self, args):
            return "HELP_TEXT_FOR: " + args

    monkeypatch.setattr(commands_mod, 'Help', FakeHelp)

    # Patch the base coder creation
    import aider.coders.base_coder as base_coder_mod

    run_called = {}
    class FakeCreatedCoderInstance:
        def run(self, user_msg, preproc=False):
            run_called['user_msg'] = user_msg
            run_called['preproc'] = preproc

    class FakeCoder:
        @staticmethod
        def create(io, from_coder, edit_format, summarize_from_coder, map_tokens, map_mul_no_files):
            # verify some of the parameters are passed as expected
            assert edit_format == "help"
            assert summarize_from_coder is False
            return FakeCreatedCoderInstance()

    monkeypatch.setattr(base_coder_mod, 'Coder', FakeCoder)

    # Now call and catch the SwitchCoder exception
    with pytest.raises(commands_mod.SwitchCoder) as excinfo:
        cmd.cmd_help("explain usage")

    # Ensure event was fired
    assert event_called.get('name') == 'interactive help'

    ex = excinfo.value
    # SwitchCoder stores passed kwargs in .kwargs
    kw = ex.kwargs
    # Check SwitchCoder kwargs that the function sets
    assert kw['edit_format'] == cmd.coder.edit_format
    assert kw['summarize_from_coder'] is False
    assert kw['from_coder'] is not None
    # Since repo_map was None, verify that the map values are the fallback ones
    assert kw['map_tokens'] == 0
    assert kw['map_mul_no_files'] == 1

    # verify that the created coder's run was called with the expected message
    assert "HELP_TEXT_FOR: explain usage" in run_called.get('user_msg', "")
    # announcements should have been appended
    assert "ANN1" in run_called.get('user_msg', "")
    assert run_called.get('preproc') is False


def test_cmd_help_uses_repo_map_values_for_map_tokens_and_mul(monkeypatch):
    cmd = make_commands_instance()

    class DummyCoder:
        def __init__(self):
            self.edit_format = "fmt-2"
            # Provide a repo_map with specific max_map_tokens and map_mul_no_files
            self.repo_map = types.SimpleNamespace(max_map_tokens=9999, map_mul_no_files=7)

        def event(self, name):
            pass

        def get_announcements(self):
            return []

    cmd.coder = DummyCoder()
    cmd.io = object()
    cmd.help = None

    # Patch install_help_extra to succeed and Help.ask to return something
    monkeypatch.setattr(commands_mod, 'install_help_extra', lambda io: True)

    class FakeHelp2:
        def ask(self, args):
            return "OK"

    monkeypatch.setattr(commands_mod, 'Help', FakeHelp2)

    import aider.coders.base_coder as base_coder_mod

    class FakeCoder2:
        @staticmethod
        def create(io, from_coder, edit_format, summarize_from_coder, map_tokens, map_mul_no_files):
            return types.SimpleNamespace(run=lambda user_msg, preproc=False: None)

    monkeypatch.setattr(base_coder_mod, 'Coder', FakeCoder2)

    with pytest.raises(commands_mod.SwitchCoder) as excinfo:
        cmd.cmd_help("some question")

    ex = excinfo.value
    kw = ex.kwargs
    # Should take tokens from repo_map
    assert kw['map_tokens'] == 9999
    assert kw['map_mul_no_files'] == 7
    assert kw['from_coder'] is not None
    assert kw['edit_format'] == cmd.coder.edit_format
