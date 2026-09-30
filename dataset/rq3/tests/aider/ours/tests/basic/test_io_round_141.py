import builtins
import pytest
import aider.io as io_module
from aider.io import InputOutput

# Helper to create an InputOutput instance without running its heavy __init__
def make_io_instance():
    inst = object.__new__(InputOutput)
    # read_text only depends on .encoding, .read_image, and .tool_error
    inst.encoding = "utf-8"
    return inst


def _fake_open_raiser(exc):
    def opener(*args, **kwargs):
        raise exc
    return opener


def test_read_image_round_141(monkeypatch):
    # If is_image_file returns True, read_text should delegate to read_image
    monkeypatch.setattr(io_module, "is_image_file", lambda filename: True)
    inst = make_io_instance()
    called = {}

    def fake_read_image(fname):
        called['fname'] = fname
        return "IMGDATA:single"

    inst.read_image = fake_read_image

    result = inst.read_text("pic.png")
    assert result == "IMGDATA:single"
    assert called['fname'] == "pic.png"


def test_file_not_found_calls_tool_error_round_141(monkeypatch):
    # open raises FileNotFoundError -> tool_error called once with specific message
    monkeypatch.setattr(io_module, "is_image_file", lambda filename: False)
    monkeypatch.setattr(builtins, "open", _fake_open_raiser(FileNotFoundError()), raising=True)

    inst = make_io_instance()
    recorded = []
    inst.tool_error = lambda message: recorded.append(message)

    res = inst.read_text("nofile.txt", silent=False)
    assert res is None
    assert recorded == ["nofile.txt: file not found error"]


def test_file_not_found_silent_true_round_141(monkeypatch):
    # silent=True should suppress tool_error calls
    monkeypatch.setattr(io_module, "is_image_file", lambda filename: False)
    monkeypatch.setattr(builtins, "open", _fake_open_raiser(FileNotFoundError()), raising=True)

    inst = make_io_instance()
    recorded = []
    inst.tool_error = lambda message: recorded.append(message)

    res = inst.read_text("nofile.txt", silent=True)
    assert res is None
    assert recorded == []


def test_is_a_directory_round_141(monkeypatch):
    # open raises IsADirectoryError -> specific tool_error message
    monkeypatch.setattr(io_module, "is_image_file", lambda filename: False)
    monkeypatch.setattr(builtins, "open", _fake_open_raiser(IsADirectoryError()), raising=True)

    inst = make_io_instance()
    recorded = []
    inst.tool_error = lambda message: recorded.append(message)

    res = inst.read_text("somedir", silent=False)
    assert res is None
    assert recorded == ["somedir: is a directory"]


def test_oserror_round_141(monkeypatch):
    # open raises OSError('boom') -> tool_error reports the underlying message
    monkeypatch.setattr(io_module, "is_image_file", lambda filename: False)
    monkeypatch.setattr(builtins, "open", _fake_open_raiser(OSError("boom")), raising=True)

    inst = make_io_instance()
    recorded = []
    inst.tool_error = lambda message: recorded.append(message)

    res = inst.read_text("afile", silent=False)
    assert res is None
    # OSError message should be included verbatim
    assert recorded == ["afile: unable to read: boom"]


def test_unicode_error_calls_two_tool_error_round_141(monkeypatch):
    # open raises UnicodeError -> two tool_error calls with expected messages
    monkeypatch.setattr(io_module, "is_image_file", lambda filename: False)
    monkeypatch.setattr(builtins, "open", _fake_open_raiser(UnicodeError("bad")), raising=True)

    inst = make_io_instance()
    recorded = []
    inst.tool_error = lambda message: recorded.append(message)

    res = inst.read_text("enc.txt", silent=False)
    assert res is None
    assert recorded == ["enc.txt: bad", "Use --encoding to set the unicode encoding."]
