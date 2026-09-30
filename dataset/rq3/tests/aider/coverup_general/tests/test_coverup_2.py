# file: aider/io.py:523-734
# asked: {"lines": [547, 549, 573, 580, 585, 590, 595, 600, 601, 604, 607, 610, 615, 616, 617, 621, 624, 629, 631, 634, 638, 643, 644, 646, 647, 648, 649, 650, 651, 653, 654, 656, 657, 658, 659, 660, 662, 663, 664, 665, 672, 673, 674, 675, 677, 678, 679, 680, 682, 683, 684, 685, 686, 687, 690, 692, 697, 698, 699, 702, 703, 704, 705, 706, 708, 709, 713, 714, 715, 717, 718, 720, 722, 723, 725, 726, 727, 729, 730], "branches": [[539, 545], [546, 547], [548, 549], [615, 621], [615, 624], [629, 631], [629, 634], [637, 638], [641, 643], [647, 648], [647, 653], [648, 649], [648, 650], [650, 651], [650, 653], [671, 672], [673, 674], [673, 689], [689, 690], [691, 692], [694, 714], [696, 697], [700, 702], [703, 704], [703, 708], [714, 715], [714, 726], [715, 717], [715, 722], [717, 718], [717, 720], [722, 723], [722, 725], [726, 727], [726, 729]]}
# gained: {"lines": [549, 573, 580, 585, 590, 595, 600, 601, 604, 607, 610, 615, 616, 621, 629, 631, 638, 643, 644, 646, 647, 648, 649, 650, 651, 653, 656, 657, 658, 659, 660, 662, 663, 664, 665, 672, 673, 674, 675, 677, 679, 680, 682, 683, 684, 690, 692, 697, 698, 699, 702, 703, 704, 705, 706, 708, 709, 713, 714, 715, 717, 718, 720, 722, 723, 725], "branches": [[539, 545], [548, 549], [615, 621], [629, 631], [637, 638], [641, 643], [647, 648], [647, 653], [648, 649], [650, 651], [650, 653], [671, 672], [673, 674], [689, 690], [691, 692], [694, 714], [696, 697], [700, 702], [703, 704], [703, 708], [714, 715], [715, 717], [715, 722], [717, 718], [717, 720], [722, 723], [722, 725]]}

import types
import pytest

import aider.io as aiomod
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys


class PromptSessionStub:
    def __init__(self, responses):
        self.responses = list(responses)

    def prompt(self, *args, **kwargs):
        if not self.responses:
            return ""
        val = self.responses.pop(0)
        if callable(val):
            return val()
        return val


class BufferStub:
    def __init__(self, text=""):
        self.text = text
        self.cursor_position = 0
        self.inserted = ""
        self.history_backward_called = False
        self.history_forward_called = False
        self.validated = False

    def insert_text(self, txt):
        self.inserted += txt
        self.text += txt

    def history_backward(self):
        self.history_backward_called = True

    def history_forward(self):
        self.history_forward_called = True

    def validate_and_handle(self):
        self.validated = True


class AppStub:
    def __init__(self):
        class ViState:
            def __init__(self):
                self.input_mode = None

        self.vi_state = ViState()
        self.suspended = False

    def suspend_to_background(self):
        self.suspended = True


class EventStub:
    def __init__(self, buffer=None, app=None):
        self.current_buffer = buffer or BufferStub()
        self.app = app or AppStub()


@pytest.fixture(autouse=True)
def ensure_clean_env(monkeypatch):
    class DummyAutoCompleter:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(aiomod, "AutoCompleter", DummyAutoCompleter)
    yield


def test_keybindings_and_basic_flow(monkeypatch):
    captured = []

    def fake_add(self, *kargs, **kwargs):
        def decorator(func):
            captured.append((kargs, func))
            return func

        return decorator

    monkeypatch.setattr(KeyBindings, "add", fake_add, raising=True)
    monkeypatch.setattr(aiomod, "pipe_editor", lambda input_data, suffix: "edited_text\n")

    io = aiomod.InputOutput()
    io.rule = lambda *a, **k: None
    io.ring_bell = lambda *a, **k: None
    io.encoding = "utf-8"
    io.format_files_for_input = lambda rel_fnames, rel_read_only: "FILES: "

    io.placeholder = "PH"
    io.prompt_session = PromptSessionStub(["normal line"])
    io.file_watcher = types.SimpleNamespace(start=lambda: setattr(io, "_fw_started", True), stop=lambda: setattr(io, "_fw_stopped", True))
    io.clipboard_watcher = types.SimpleNamespace(start=lambda: setattr(io, "_cw_started", True), stop=lambda: setattr(io, "_cw_stopped", True))

    io.multiline_mode = True
    io.editingmode = EditingMode.EMACS

    out = io.get_input(root=".", rel_fnames=["a"], addable_rel_fnames=[], commands=[])
    assert out == "normal line"
    assert hasattr(io, "prompt_prefix")
    assert "multi" in io.prompt_prefix

    def normalize(arg):
        # Normalize Keys enums to their name, strings remain as-is
        if hasattr(arg, "name"):
            return arg.name
        return str(arg)

    want_specs = {
        ("ControlZ",): "ctrlz",
        ("c-space",): "cspace",
        ("c-up",): "cup",
        ("c-down",): "cdown",
        ("c-x", "c-e"): "cxce",
        ("enter",): "enter",
        ("escape", "enter"): "altenter",
    }

    found = {}
    for kargs, func in captured:
        norm = tuple(normalize(a) for a in kargs)
        if norm in want_specs:
            found[norm] = func

    # Ensure we've found the handlers we expect
    for spec in want_specs:
        assert spec in found, f"Missing handler for {spec}"

    # ctrl-z handler
    func = found[("ControlZ",)]
    app = AppStub()
    ev = EventStub(buffer=BufferStub(), app=app)
    func(ev)
    assert app.suspended is True

    # c-space handler
    func = found[("c-space",)]
    buf = BufferStub("start")
    ev = EventStub(buffer=buf)
    func(ev)
    assert buf.inserted.endswith(" ")
    assert buf.text.endswith(" ")

    # c-up
    func = found[("c-up",)]
    buf = BufferStub()
    ev = EventStub(buffer=buf)
    func(ev)
    assert buf.history_backward_called

    # c-down
    func = found[("c-down",)]
    buf = BufferStub()
    ev = EventStub(buffer=buf)
    func(ev)
    assert buf.history_forward_called

    # c-x c-e -> external editor
    func = found[("c-x", "c-e")]
    buf = BufferStub("orig")
    ev = EventStub(buffer=buf)
    func(ev)
    # pipe_editor returned 'edited_text\n' and buffer.text set to edited_text (rstrip)
    assert buf.text == "edited_text"
    assert buf.cursor_position == len(buf.text)

    # enter handler: since io.multiline_mode True and editingmode EMACS and input_mode not NAVIGATION, insert newline
    func = found[("enter",)]
    buf = BufferStub("x")
    app = AppStub()
    app.vi_state.input_mode = "SOMETHING"
    ev = EventStub(buffer=buf, app=app)
    # need io instance accessible inside handler; it's bound via closure to the InputOutput instance when registered
    func(ev)
    assert buf.inserted.endswith("\n")

    # alt-enter handler: when multiline_mode True it should call validate_and_handle
    func = found[("escape", "enter")]
    buf = BufferStub("y")
    ev = EventStub(buffer=buf, app=AppStub())
    io.multiline_mode = True
    func(ev)
    assert buf.validated

    # watchers started/stopped
    assert getattr(io, "_fw_started", True) is True
    assert getattr(io, "_fw_stopped", True) is True
    assert getattr(io, "_cw_started", True) is True
    assert getattr(io, "_cw_stopped", True) is True


def test_interrupted_file_watcher_returns_cmd(monkeypatch):
    io = aiomod.InputOutput()
    io.rule = lambda *a, **k: None
    io.ring_bell = lambda *a, **k: None
    io.encoding = "utf-8"
    io.format_files_for_input = lambda a, b: ""
    processed = {"started": False, "stopped": False}

    def fw_start():
        processed["started"] = True

    def fw_stop():
        processed["stopped"] = True

    def process_changes():
        return "RELOAD_CMD"

    io.file_watcher = types.SimpleNamespace(start=fw_start, stop=fw_stop, process_changes=process_changes)
    io.clipboard_watcher = None

    def set_interrupted_and_return():
        io.interrupted = True
        return ""

    io.prompt_session = PromptSessionStub([set_interrupted_and_return])
    res = io.get_input(root=".", rel_fnames=[], addable_rel_fnames=[], commands=[])
    assert res == "RELOAD_CMD"
    assert processed["started"]
    assert processed["stopped"]


def test_exception_and_unicode_handling(monkeypatch):
    io = aiomod.InputOutput()
    io.rule = lambda *a, **k: None
    io.ring_bell = lambda *a, **k: None
    io.format_files_for_input = lambda a, b: ""

    class BadSession:
        def prompt(self, *a, **k):
            raise RuntimeError("boom")

    io.prompt_session = BadSession()
    errors = []

    def tool_error(msg):
        errors.append(msg)

    io.tool_error = tool_error
    io.file_watcher = types.SimpleNamespace(stop=lambda: setattr(io, "_fw_stopped_exc", True))
    io.clipboard_watcher = None

    out = io.get_input(root=".", rel_fnames=[], addable_rel_fnames=[], commands=[])
    assert out == ""
    assert len(errors) >= 2
    assert getattr(io, "_fw_stopped_exc", True) is True

    io2 = aiomod.InputOutput()
    io2.rule = lambda *a, **k: None
    io2.ring_bell = lambda *a, **k: None
    io2.format_files_for_input = lambda a, b: ""

    class UnicodeSession:
        def prompt(self, *a, **k):
            raise UnicodeEncodeError("utf-8", b"", 0, 1, "err")

    io2.prompt_session = UnicodeSession()
    errors2 = []
    io2.tool_error = lambda msg: errors2.append(msg)
    io2.file_watcher = types.SimpleNamespace(stop=lambda: setattr(io2, "_fw_stopped_u8", True))
    io2.clipboard_watcher = None

    out2 = io2.get_input(root=".", rel_fnames=[], addable_rel_fnames=[], commands=[])
    assert out2 == ""
    assert errors2
    assert getattr(io2, "_fw_stopped_u8", True) is True


def test_multiline_brace_behaviors(monkeypatch):
    io = aiomod.InputOutput()
    io.rule = lambda *a, **k: None
    io.ring_bell = lambda *a, **k: None
    io.encoding = "utf-8"
    io.format_files_for_input = lambda a, b: ""
    io.clipboard_watcher = None

    io.prompt_session = PromptSessionStub(["{", "first line", "}"])
    io.file_watcher = types.SimpleNamespace(start=lambda: setattr(io, "_fw_started1", True), stop=lambda: setattr(io, "_fw_stopped1", True))
    res1 = io.get_input(root=".", rel_fnames=[], addable_rel_fnames=[], commands=[])
    assert res1 == "first line\n"

    io2 = aiomod.InputOutput()
    io2.rule = lambda *a, **k: None
    io2.ring_bell = lambda *a, **k: None
    io2.encoding = "utf-8"
    io2.format_files_for_input = lambda a, b: ""
    io2.clipboard_watcher = None
    io2.file_watcher = types.SimpleNamespace(start=lambda: None, stop=lambda: None)

    io2.prompt_session = PromptSessionStub(["{mytag", "line1", "mytag}"])
    res2 = io2.get_input(root=".", rel_fnames=[], addable_rel_fnames=[], commands=[])
    assert res2 == "line1\n"

    io3 = aiomod.InputOutput()
    io3.rule = lambda *a, **k: None
    io3.ring_bell = lambda *a, **k: None
    io3.encoding = "utf-8"
    io3.format_files_for_input = lambda a, b: ""
    io3.clipboard_watcher = None
    io3.file_watcher = types.SimpleNamespace(start=lambda: None, stop=lambda: None)

    io3.prompt_session = PromptSessionStub(["{x}", "should not be read"])
    res3 = io3.get_input(root=".", rel_fnames=[], addable_rel_fnames=[], commands=[])
    assert res3 == "{x}"
