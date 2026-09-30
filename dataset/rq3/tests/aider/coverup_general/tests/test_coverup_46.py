# file: aider/gui.py:187-208
# asked: {"lines": [187, 188, 189, 190, 191, 192, 193, 195, 200, 201, 202, 203, 205, 206, 207, 208], "branches": [[200, 201], [200, 205], [201, 200], [201, 202], [205, 0], [205, 206], [206, 205], [206, 207]]}
# gained: {"lines": [187, 188, 189, 190, 191, 192, 193, 195, 200, 201, 202, 203, 205, 206, 207, 208], "branches": [[200, 201], [200, 205], [201, 200], [201, 202], [205, 0], [205, 206], [206, 205], [206, 207]]}

import importlib
import sys
import types

import pytest


class FakeCoder:
    def __init__(self, all_files=None, inchat=None):
        self._all_files = list(all_files) if all_files else []
        self._inchat = list(inchat) if inchat else []
        self.added = []
        self.dropped = []

    def get_all_relative_files(self):
        return list(self._all_files)

    def get_inchat_relative_files(self):
        return list(self._inchat)

    def add_rel_fname(self, fname):
        self.added.append(fname)
        if fname not in self._inchat:
            self._inchat.append(fname)

    def drop_rel_fname(self, fname):
        self.dropped.append(fname)
        if fname in self._inchat:
            self._inchat.remove(fname)


class DummyState:
    def __init__(self, initial_inchat_files):
        self.initial_inchat_files = list(initial_inchat_files)


def import_gui_with_stub_streamlit(multiselect_func, monkeypatch):
    """
    Inject a fake 'streamlit' module exposing needed attributes and import (fresh) aider.gui
    so its 'st' refers to our stub.
    """
    fake_st = types.ModuleType("streamlit")
    # Provide a cache_resource that can be used as a decorator, with or without args
    def cache_resource(*cargs, **kwargs):
        def _decorator(f):
            return f
        return _decorator
    fake_st.cache_resource = cache_resource
    # Provide a placeholder for multiselect which will be overwritten below
    fake_st.multiselect = multiselect_func

    # Put our fake streamlit into sys.modules before importing aider.gui
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)
    # Ensure a fresh import of aider.gui so it binds to our fake streamlit
    if "aider.gui" in sys.modules:
        monkeypatch.delitem(sys.modules, "aider.gui")
    module = importlib.import_module("aider.gui")
    return module


def test_do_add_files_adds_new_file_and_keeps_existing(monkeypatch):
    coder = FakeCoder(all_files=["a.py", "b.py", "c.py"], inchat=["b.py"])
    state = DummyState(initial_inchat_files=["b.py"])
    info_messages = []

    def prompt_pending():
        return False

    def info(msg):
        info_messages.append(msg)

    def multiselect(label, options, default=None, placeholder=None, disabled=None, help=None):
        # Validate parameters passed from the function under test
        assert label == "Add files to the chat"
        assert options == coder.get_all_relative_files()
        assert default == state.initial_inchat_files
        assert placeholder == "Files to edit"
        assert disabled is False
        # Return selection: keep 'b.py' and add 'a.py'
        return ["b.py", "a.py"]

    gui_mod = import_gui_with_stub_streamlit(multiselect, monkeypatch)
    do_add_files_func = gui_mod.GUI.do_add_files

    fake_self = types.SimpleNamespace()
    fake_self.coder = coder
    fake_self.state = state
    fake_self.prompt_pending = prompt_pending
    fake_self.info = info

    do_add_files_func(fake_self)

    assert coder.added == ["a.py"]
    assert coder.dropped == []
    assert "Added a.py to the chat" in info_messages
    assert set(coder.get_inchat_relative_files()) == {"a.py", "b.py"}


def test_do_add_files_removes_missing_file_and_disabled_true(monkeypatch):
    coder = FakeCoder(all_files=["a.py", "b.py"], inchat=["a.py", "b.py"])
    state = DummyState(initial_inchat_files=["a.py", "b.py"])
    info_messages = []

    def prompt_pending():
        return True

    def info(msg):
        info_messages.append(msg)

    def multiselect(label, options, default=None, placeholder=None, disabled=None, help=None):
        assert label == "Add files to the chat"
        assert options == coder.get_all_relative_files()
        assert default == state.initial_inchat_files
        assert placeholder == "Files to edit"
        assert disabled is True
        # Return selection missing 'a.py' so it gets dropped
        return ["b.py"]

    gui_mod = import_gui_with_stub_streamlit(multiselect, monkeypatch)
    do_add_files_func = gui_mod.GUI.do_add_files

    fake_self = types.SimpleNamespace()
    fake_self.coder = coder
    fake_self.state = state
    fake_self.prompt_pending = prompt_pending
    fake_self.info = info

    do_add_files_func(fake_self)

    assert coder.added == []
    assert coder.dropped == ["a.py"]
    assert "Removed a.py from the chat" in info_messages
    assert coder.get_inchat_relative_files() == ["b.py"]
