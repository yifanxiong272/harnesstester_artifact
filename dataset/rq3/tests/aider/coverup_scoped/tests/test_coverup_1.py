# file: aider/io.py:523-734
# asked: {"lines": [547, 549, 573, 580, 585, 590, 595, 600, 601, 604, 607, 610, 615, 616, 617, 621, 624, 629, 631, 634, 638, 643, 644, 646, 647, 648, 649, 650, 651, 653, 654, 656, 657, 658, 659, 660, 662, 663, 664, 665, 672, 673, 674, 675, 677, 678, 679, 680, 682, 683, 684, 685, 686, 687, 690, 692, 697, 698, 699, 702, 703, 704, 705, 706, 708, 709, 713, 714, 715, 717, 718, 720, 722, 723, 725, 726, 727, 729, 730], "branches": [[539, 545], [546, 547], [548, 549], [615, 621], [615, 624], [629, 631], [629, 634], [637, 638], [641, 643], [647, 648], [647, 653], [648, 649], [648, 650], [650, 651], [650, 653], [671, 672], [673, 674], [673, 689], [689, 690], [691, 692], [694, 714], [696, 697], [700, 702], [703, 704], [703, 708], [714, 715], [714, 726], [715, 717], [715, 722], [717, 718], [717, 720], [722, 723], [722, 725], [726, 727], [726, 729]]}
# gained: {"lines": [547, 549, 573, 580, 585, 590, 595, 600, 601, 604, 607, 610, 615, 624, 629, 634, 638, 643, 644, 646, 647, 648, 649, 650, 651, 653, 656, 657, 658, 659, 660, 662, 663, 664, 665, 672, 673, 674, 675, 677, 679, 680, 682, 683, 684, 690, 692, 697, 698, 699, 702, 703, 704, 705, 706, 708, 709, 713, 714, 715, 717, 718, 720, 722, 723, 725], "branches": [[539, 545], [546, 547], [548, 549], [615, 624], [629, 634], [637, 638], [641, 643], [647, 648], [647, 653], [648, 649], [648, 650], [650, 651], [650, 653], [671, 672], [673, 674], [689, 690], [691, 692], [694, 714], [696, 697], [700, 702], [703, 704], [703, 708], [714, 715], [715, 717], [715, 722], [717, 718], [717, 720], [722, 723], [722, 725]]}

import builtins
import types
import traceback

import pytest

import aider.io as io_mod
from aider.io import InputOutput
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.key_binding.vi_state import InputMode


class DummyBuffer:
    def __init__(self, text=""):
        self.text = text
        self.cursor_position = 0
        self.inserted = []
        self.history_back_called = False
        self.history_forward_called = False
        self.validated = False

    def insert_text(self, txt):
        # emulate insertion by appending to text and record for assertions
        self.inserted.append(txt)
        self.text += txt

    def history_backward(self):
        self.history_back_called = True

    def history_forward(self):
        self.history_forward_called = True

    def validate_and_handle(self):
        self.validated = True


class DummyApp:
    def __init__(self, vi_input_mode=None):
        self._suspended = False
        self.vi_state = types.SimpleNamespace(input_mode=vi_input_mode or InputMode.INSERT)

    def suspend_to_background(self):
        self._suspended = True


class DummyEvent:
    def __init__(self, buffer=None, app=None):
        self.current_buffer = buffer or DummyBuffer()
        self.app = app or DummyApp()


class FakeKeyBindings:
    """
    Fake KeyBindings factory replacement. Its .add decorator will call the decorated
    function immediately with an appropriate DummyEvent depending on the docstring.
    This triggers execution of nested handler bodies inside get_input().
    """

    def __init__(self):
        # collect events used for assertions
        self.events = []

    def add(self, *args, **kwargs):
        # return decorator
        def decorator(f):
            doc = (f.__doc__ or "").strip()

            # choose event based on docstring heuristics
            if "Suspend to background" in doc:
                ev = DummyEvent(app=DummyApp())
            elif "Ctrl when pressing space" in doc:
                ev = DummyEvent(buffer=DummyBuffer("start"))
            elif "Navigate backward" in doc:
                ev = DummyEvent(buffer=DummyBuffer("start"))
            elif "Navigate forward" in doc:
                ev = DummyEvent(buffer=DummyBuffer("start"))
            elif "external editor" in doc:
                ev = DummyEvent(buffer=DummyBuffer("original"))
            elif "Handle Enter key press" in doc:
                ev = DummyEvent(buffer=DummyBuffer("e1"), app=DummyApp())
            elif "Handle Alt+Enter" in doc:
                ev = DummyEvent(buffer=DummyBuffer("e2"), app=DummyApp())
            else:
                ev = DummyEvent()

            self.events.append((f.__name__, doc, ev))
            # call the function with the event to execute its body now
            try:
                f(ev)
            except Exception:
                # don't fail decoration; capture for debugging if needed
                pass
            return f

        return decorator


def make_input_output_instance():
    inst = InputOutput()
    # provide simple implementations/attributes that are used
    # these exist on the class, but ensure they are harmless
    inst.encoding = "utf-8"
    inst.rule = lambda: None
    inst.ring_bell = lambda: None
    inst.user_input = lambda s: setattr(inst, "_last_user_input", s)
    inst._get_style = lambda: None
    inst.placeholder = None
    inst.prompt_session = None
    inst.file_watcher = None
    inst.clipboard_watcher = None
    inst.prompt_prefix = ""
    inst.prompt_session = None
    inst.editingmode = EditingMode.EMACS
    inst.multiline_mode = False
    return inst


def test_get_input_simple_input_and_prompt_prefix(monkeypatch):
    inst = make_input_output_instance()
    # ensure rel_fnames truthy branch and format_files_for_input used
    inst.format_files_for_input = lambda rel, rel_ro: "FILES: "
    # capture user_input call
    called = {}

    def user_input(s):
        called['val'] = s

    inst.user_input = user_input

    # simulate input(...) returning a simple line
    monkeypatch.setattr(builtins, "input", lambda prompt="": "hello")

    res = inst.get_input(root="/tmp", rel_fnames=["a"], addable_rel_fnames=[], commands=[])
    assert res == "hello"
    assert called["val"] == "hello"
    # prompt prefix should include edit_format when given
    inst2 = make_input_output_instance()
    inst2.format_files_for_input = lambda rel, rel_ro: ""
    monkeypatch.setattr(builtins, "input", lambda prompt="": "x")
    res2 = inst2.get_input(root="/tmp", rel_fnames=["b"], addable_rel_fnames=[], commands=[], edit_format="fmt")
    assert res2 == "x"
    assert inst2.prompt_prefix.startswith("fmt")
    assert inst.prompt_prefix.endswith("> ")


def test_keybinding_handlers_and_pipe_editor(monkeypatch):
    inst = make_input_output_instance()
    # set up ThreadedCompleter to be a no-op to avoid heavy imports
    monkeypatch.setattr(io_mod, "ThreadedCompleter", lambda x: x)
    # replace KeyBindings with our fake that calls handlers immediately
    fake_kb = FakeKeyBindings()
    monkeypatch.setattr(io_mod, "KeyBindings", lambda: fake_kb)
    # replace pipe_editor to return some edited content
    monkeypatch.setattr(io_mod, "pipe_editor", lambda input_data, suffix=None: "edited_text\n")
    # create prompt_session stub that returns a line and will cause early exit
    class PromptSessionStub:
        def prompt(self, *args, **kwargs):
            return "final_line"

    inst.prompt_session = PromptSessionStub()
    # ensure we take the validate_and_handle path for enter handler
    inst.multiline_mode = False
    inst.editingmode = EditingMode.EMACS
    # call get_input with a non-empty rel_fnames so prompt_prefix constructed
    res = inst.get_input(root=".", rel_fnames=["file"], addable_rel_fnames=[], commands=[])
    # ensure returned value equals what prompt returned
    assert res == "final_line"
    # verify that fake_kb created events and that pipe_editor replaced buffer.text
    # look for the event created for "external editor"
    found_pipe = False
    for name, doc, ev in fake_kb.events:
        if "external editor" in doc:
            found_pipe = True
            # buffer text should have been set to cleaned edited_text by handler
            assert ev.current_buffer.text == "edited_text"
            assert ev.current_buffer.cursor_position == len("edited_text")
    assert found_pipe


def test_prompt_session_exception_and_unicode(monkeypatch):
    inst = make_input_output_instance()
    # stub ThreadedCompleter
    monkeypatch.setattr(io_mod, "ThreadedCompleter", lambda x: x)
    # create prompt_session that raises a generic Exception first, then UnicodeEncodeError
    class PromptSessionErr:
        def __init__(self, exc):
            self.exc = exc

        def prompt(self, *args, **kwargs):
            raise self.exc

    # record tool_error calls
    calls = []

    def tool_error(msg):
        calls.append(msg)

    inst.tool_error = tool_error

    # have watchers to ensure stop() called in finally
    class FW:
        def __init__(self):
            self.started = False
            self.stopped = False

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

    class CW:
        def __init__(self):
            self.started = False
            self.stopped = False

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

    fw = FW()
    cw = CW()
    inst.file_watcher = fw
    inst.clipboard_watcher = cw
    # test generic exception path
    inst.prompt_session = PromptSessionErr(Exception("boom"))
    r = inst.get_input(root=".", rel_fnames=[], addable_rel_fnames=[], commands=[])
    # should return empty string on generic exception and tool_error called with traceback
    assert r == ""
    assert any("boom" in (c if isinstance(c, str) else "") for c in calls)
    # clear and test UnicodeEncodeError
    calls.clear()
    # construct UnicodeEncodeError with a str object for the second argument
    inst.prompt_session = PromptSessionErr(UnicodeEncodeError("utf-8", "a", 0, 1, "reason"))
    r2 = inst.get_input(root=".", rel_fnames=[], addable_rel_fnames=[], commands=[])
    assert r2 == ""
    # ensure that tool_error was called with some message mentioning reason or encoding
    assert any("reason" in (c if isinstance(c, str) else "") or "utf-8" in (c if isinstance(c, str) else "") for c in calls)


def test_interrupted_file_watcher_process_changes(monkeypatch):
    inst = make_input_output_instance()
    monkeypatch.setattr(io_mod, "ThreadedCompleter", lambda x: x)

    # create a prompt_session that will set inst.interrupted True and return empty line
    class PromptSessionInterrupt:
        def prompt(self, *args, **kwargs):
            inst.interrupted = True
            return ""

    inst.prompt_session = PromptSessionInterrupt()
    # file_watcher returns a command on process_changes
    fw_called = {}
    class FW:
        def start(self):
            fw_called['started'] = True

        def stop(self):
            fw_called['stopped'] = True

        def process_changes(self):
            fw_called['processed'] = True
            return "RESTART_CMD"

    cw = types.SimpleNamespace(start=lambda: setattr(cw, "s", True), stop=lambda: setattr(cw, "t", True))
    inst.file_watcher = FW()
    inst.clipboard_watcher = cw
    res = inst.get_input(root=".", rel_fnames=[], addable_rel_fnames=[], commands=[])
    assert res == "RESTART_CMD"
    # ensure start and stop were invoked on watchers
    assert fw_called.get('started', False) is True
    # stop in finally should have run
    assert fw_called.get('stopped', False) is True


def test_multiline_brace_and_tag_handling(monkeypatch):
    inst = make_input_output_instance()
    monkeypatch.setattr(io_mod, "ThreadedCompleter", lambda x: x)

    # Test multiline with plain '{' then 'line' then '}' -> should produce "line\n"
    seq = ["{", "line1", "}"]

    class PSSeq:
        def prompt(self, *args, **kwargs):
            return seq.pop(0)

    inst.prompt_session = PSSeq()
    inst.multiline_mode = True
    res = inst.get_input(root=".", rel_fnames=[], addable_rel_fnames=[], commands=[])
    assert res == "line1\n"

    # Test multiline with tag: first "{tag", then "a", then "tag}" -> should produce "a\n"
    seq2 = ["{mytag", "linea", "mytag}"]

    class PSSeq2:
        def prompt(self, *args, **kwargs):
            return seq2.pop(0)

    inst2 = make_input_output_instance()
    monkeypatch.setattr(io_mod, "ThreadedCompleter", lambda x: x)
    inst2.prompt_session = PSSeq2()
    inst2.multiline_mode = True
    res2 = inst2.get_input(root=".", rel_fnames=[], addable_rel_fnames=[], commands=[])
    assert res2 == "linea\n"

    # Test '{' with non-matching subsequent characters causing immediate single-line input
    seq3 = ["{abc!!"]

    class PSSeq3:
        def prompt(self, *args, **kwargs):
            return seq3.pop(0)

    inst3 = make_input_output_instance()
    inst3.prompt_session = PSSeq3()
    inst3.multiline_mode = True
    res3 = inst3.get_input(root=".", rel_fnames=[], addable_rel_fnames=[], commands=[])
    assert res3 == "{abc!!"
