import types
from types import SimpleNamespace
import pytest

import aider.gui as gui_mod
from aider.gui import GUI


class FakeCoder:
    def __init__(self, all_files, inchat_files):
        # keep internal lists so methods can mutate them like a real coder
        self._all = list(all_files)
        self._inchat = list(inchat_files)
        self.added = []
        self.dropped = []

    def get_all_relative_files(self):
        return list(self._all)

    def get_inchat_relative_files(self):
        return list(self._inchat)

    def add_rel_fname(self, fname):
        # emulate side-effect of adding to in-chat list
        self.added.append(fname)
        if fname not in self._inchat:
            self._inchat.append(fname)

    def drop_rel_fname(self, fname):
        self.dropped.append(fname)
        if fname in self._inchat:
            self._inchat.remove(fname)


def make_multiselect(return_value, record_holder):
    # returns a function compatible with streamlit.multiselect signature
    def _multiselect(label, options, default=None, placeholder=None, disabled=None, help=None):
        # record passed-through parameters for assertions
        record_holder['label'] = label
        record_holder['options'] = list(options)
        record_holder['default'] = list(default) if default is not None else None
        record_holder['placeholder'] = placeholder
        record_holder['disabled'] = disabled
        record_holder['help'] = help
        return list(return_value)

    return _multiselect


def prepare_gui_instance(coder, initial_inchat_files):
    # create GUI instance without invoking __init__ to avoid side effects
    gui = GUI.__new__(GUI)
    gui.coder = coder
    gui.state = SimpleNamespace(initial_inchat_files=list(initial_inchat_files))
    # prompt_pending used for disabled parameter
    gui.prompt_pending = lambda: False
    # capture info messages
    gui_info_messages = []
    gui.info = lambda msg: gui_info_messages.append(msg)
    gui._captured_info = gui_info_messages
    return gui


def test_do_add_files_adds_new_and_keeps_existing_round_099(monkeypatch):
    """
    Scenario: available files contain 'a.py' and 'b.py', in-chat initially only 'a.py'.
    The multiselect returns ['a.py', 'b.py'] -> 'b.py' should be added.
    Assertions:
      - coder.add_rel_fname called for 'b.py'
      - coder.drop_rel_fname not called
      - info was called with the expected "Added b.py to the chat" message
      - multiselect received the state's initial_inchat_files as default and disabled matches prompt_pending()
    """
    fake = FakeCoder(all_files=['a.py', 'b.py'], inchat_files=['a.py'])
    gui = prepare_gui_instance(fake, initial_inchat_files=['a.py'])

    record = {}
    fake_multiselect = make_multiselect(['a.py', 'b.py'], record)
    # patch the multiselect used by the GUI implementation
    monkeypatch.setattr(gui_mod.st, 'multiselect', fake_multiselect)

    # run the code under test
    gui.do_add_files()

    # validate coder interactions
    assert fake.added == ['b.py'], "Expected b.py to be added"
    assert fake.dropped == [], "No files should have been dropped"

    # validate info messages contain the expected Add message
    assert any('Added b.py to the chat' in m for m in gui._captured_info), gui._captured_info

    # validate multiselect called with correct default and disabled
    assert record['default'] == ['a.py']
    assert record['disabled'] is False


def test_do_add_files_removes_missing_round_099(monkeypatch):
    """
    Scenario: in-chat contains 'x.py' and 'y.py', multiselect returns only ['x.py'] -> 'y.py' should be removed.
    Assertions:
      - coder.drop_rel_fname called for 'y.py'
      - coder.add_rel_fname not called
      - info was called with the expected "Removed y.py to the chat" message
      - multiselect received the state's initial_inchat_files as default and disabled matches prompt_pending()
    """
    fake = FakeCoder(all_files=['x.py'], inchat_files=['x.py', 'y.py'])
    gui = prepare_gui_instance(fake, initial_inchat_files=['x.py', 'y.py'])

    record = {}
    fake_multiselect = make_multiselect(['x.py'], record)
    monkeypatch.setattr(gui_mod.st, 'multiselect', fake_multiselect)

    gui.do_add_files()

    # validate coder interactions
    assert fake.added == [], f"No files should have been added, got: {fake.added}"
    assert fake.dropped == ['y.py'], f"Expected y.py to be dropped, got: {fake.dropped}"

    # validate info messages contain the expected Remove message
    assert any('Removed y.py to the chat' in m or 'Removed y.py from the chat' in m for m in gui._captured_info), gui._captured_info

    # validate multiselect called with correct default and disabled
    assert record['default'] == ['x.py', 'y.py']
    assert record['disabled'] is False
