import types
import pytest

import aider.commands as commands


class FakeIO:
    def __init__(self):
        self.outputs = []

    def tool_output(self, text):
        # mimic the real io.tool_output side effect by recording output
        self.outputs.append(text)


class FakeModel:
    def __init__(self, name=None, info=None, editor_model=None, weak_model=None):
        self.name = name
        # allow info to be None, {}, or dict
        self.info = info
        if editor_model is not None:
            self.editor_model = editor_model
        if weak_model is not None:
            self.weak_model = weak_model


class FakeCoder:
    def __init__(self, announcements=None, main_model=None):
        self._ann = announcements or []
        self.main_model = main_model

    def get_announcements(self):
        return list(self._ann)


def make_commands_instance():
    # Create a Commands instance without calling its real __init__
    inst = object.__new__(commands.Commands)
    return inst


def setup_common(monkeypatch, announcements=None):
    # patch format_settings to a deterministic value
    monkeypatch.setattr(commands, "format_settings", lambda parser, args: "SETTINGS")

    inst = make_commands_instance()
    inst.parser = object()  # not used by our fake format_settings
    inst.args = object()

    fake_io = FakeIO()
    inst.io = fake_io

    fake_coder = FakeCoder(announcements=announcements or [], main_model=None)
    inst.coder = fake_coder

    return inst, fake_io


def test_cmd_settings_no_models_round_053(monkeypatch):
    # Case: coder.main_model is None -> model metadata should be empty
    inst, fake_io = setup_common(monkeypatch, announcements=["one", "two"])

    # ensure main_model is explicitly None
    inst.coder.main_model = None

    # call the method under test
    inst.cmd_settings(args=None)

    # announcements joined by newline + newline + SETTINGS expected
    expected = "one\ntwo\nSETTINGS"
    assert fake_io.outputs == [expected]


def test_cmd_settings_main_model_empty_info_round_053(monkeypatch):
    # Case: main model exists but has empty info ({} or None) -> skipped
    inst, fake_io = setup_common(monkeypatch, announcements=["A"])

    # model with empty dict info should be skipped
    inst.coder.main_model = FakeModel(name="M", info={})

    inst.cmd_settings(args=None)

    expected = "A\nSETTINGS"
    assert fake_io.outputs == [expected]

    # also test when info is None (triggers the `or {}` branch)
    fake_io.outputs.clear()
    inst.coder.main_model = FakeModel(name="M", info=None)
    inst.cmd_settings(args=None)
    assert fake_io.outputs == [expected]


def test_cmd_settings_with_models_round_053(monkeypatch):
    # Case: main model has info dict -> should produce model metadata lines
    inst, fake_io = setup_common(monkeypatch, announcements=["X"])

    # main model with unordered keys; sorting in function should order them
    main_info = {"b": 2, "a": 1}
    main = FakeModel(name="G", info=main_info)

    # editor model present with its own info to exercise multiple sections
    editor_info = {"z": 9}
    editor = FakeModel(name="E", info=editor_info)
    # attach editor model to main_model so getattr(self.coder.main_model, "editor_model", None)
    main.editor_model = editor

    inst.coder.main_model = main

    inst.cmd_settings(args=None)

    # Build expected model_metadata as the function does:
    # "Main model (G):" then sorted items a,b then blank line, then
    # "Editor model (E):" then its sorted items then blank line
    model_section = (
        "Main model (G):\n"
        "  a: 1\n"
        "  b: 2\n"
        "\n"
        "Editor model (E):\n"
        "  z: 9\n"
        "\n"
    )

    expected = "X\nSETTINGS\n" + model_section
    assert fake_io.outputs == [expected]
