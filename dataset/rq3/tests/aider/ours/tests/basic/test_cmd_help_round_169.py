import sys
import types
import pytest
from types import SimpleNamespace

import aider.commands as commands
from aider.commands import Commands, SwitchCoder


def make_fake_base_coder_module(create_return=None):
    """Create a fake module to satisfy `from aider.coders.base_coder import Coder`.
    The Coder returned will have a .create(...) classmethod that returns
    create_return (or a simple default fake coder).
    """
    mod = types.ModuleType("aider.coders.base_coder")

    class FakeCoderCls:
        @staticmethod
        def create(**kwargs):
            return create_return

    mod.Coder = FakeCoderCls
    return mod


def test_basic_help_branch_round_169():
    # Arrange: create a lightweight self object with basic_help callable
    self_obj = SimpleNamespace()
    called = {}

    def basic_help():
        called['v'] = True

    self_obj.basic_help = basic_help

    # Act: call cmd_help with whitespace-only args -> should call basic_help and return
    result = Commands.cmd_help(self_obj, "   ")

    # Assert
    assert called.get('v', False) is True
    assert result is None


def test_install_help_fails_round_169(monkeypatch):
    # Arrange: ensure import inside cmd_help won't fail by providing a fake base_coder module
    fake_mod = make_fake_base_coder_module()
    sys.modules['aider.coders.base_coder'] = fake_mod

    called = {}

    # prepare self object
    io = SimpleNamespace()

    def tool_error(msg):
        called['err'] = msg

    io.tool_error = tool_error

    coder = SimpleNamespace()
    coder.event_called = []

    def event(name):
        coder.event_called.append(name)

    coder.event = event

    # self.help falsy so install_help_extra will be called
    self_obj = SimpleNamespace()
    self_obj.io = io
    self_obj.coder = coder
    self_obj.help = False

    # Patch install_help_extra to return False (initialization failed)
    monkeypatch.setattr(commands, 'install_help_extra', lambda io: False)

    # Act: call cmd_help with non-empty args
    result = Commands.cmd_help(self_obj, "how does help work?")

    # Assert: coder.event should have been called and io.tool_error invoked with the expected message
    assert coder.event_called == ["interactive help"]
    assert called.get('err') == "Unable to initialize interactive help."
    assert result is None


def test_full_flow_repo_map_false_round_169(monkeypatch):
    # Arrange: create fake new coder that records run() input
    class FakeNewCoder:
        def __init__(self):
            self.run_called = None

        def run(self, msg, preproc=True):
            # record call parameters
            self.run_called = dict(msg=msg, preproc=preproc)

    new_coder_instance = FakeNewCoder()

    # Provide fake base_coder module whose Coder.create returns our new coder
    fake_mod = make_fake_base_coder_module(create_return=new_coder_instance)
    sys.modules['aider.coders.base_coder'] = fake_mod

    # Patch Help to produce a predictable ask result
    class FakeHelp:
        def ask(self, args):
            return "FAKE_HELP_FOR: " + args

    monkeypatch.setattr(commands, 'Help', FakeHelp)
    monkeypatch.setattr(commands, 'install_help_extra', lambda io: True)

    # Prepare original coder (self.coder) with repo_map falsy to hit else branch
    original_coder = SimpleNamespace()
    original_coder.event_called = []

    def event(name):
        original_coder.event_called.append(name)

    original_coder.event = event
    original_coder.get_announcements = lambda: ["ann1", "ann2"]
    original_coder.edit_format = 'orig-format'
    original_coder.repo_map = None  # falsy -> should select map_tokens=0, map_mul_no_files=1

    io = SimpleNamespace()

    # Build self object used as 'self' by the unbound function
    self_obj = SimpleNamespace()
    self_obj.io = io
    self_obj.coder = original_coder
    self_obj.help = False

    # Act & Assert: expect SwitchCoder to be raised with certain attributes
    with pytest.raises(SwitchCoder) as excinfo:
        Commands.cmd_help(self_obj, "explain X")

    exc = excinfo.value

    # The SwitchCoder should carry the passed kwargs as attributes (map tokens/mul)
    assert getattr(exc, 'map_tokens', None) == 0
    assert getattr(exc, 'map_mul_no_files', None) == 1
    # check that the 'from_coder' attached to the exception is the coder created by Coder.create
    assert getattr(exc, 'from_coder', None) is new_coder_instance
    # check edit_format forwarded from original coder
    assert getattr(exc, 'edit_format', None) == original_coder.edit_format

    # Also ensure our new coder's run() was invoked with the composed user message
    # The run call should have been recorded on the fake new coder instance
    assert new_coder_instance.run_called is not None
    run_msg = new_coder_instance.run_called['msg']
    # should include the help.ask return and announcements
    assert "FAKE_HELP_FOR: explain X" in run_msg
    assert "ann1" in run_msg and "ann2" in run_msg
    assert new_coder_instance.run_called['preproc'] is False
