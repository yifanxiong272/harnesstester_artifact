# file: aider/io.py:453-476
# asked: {"lines": [465, 466, 467, 469, 470, 471], "branches": [[461, 463], [465, 466], [465, 467], [469, 470], [469, 471], [473, 476]]}
# gained: {"lines": [465, 466, 467, 469, 470, 471], "branches": [[465, 466], [469, 470]]}

import builtins
import pytest

import aider.io as aio
import aider.utils as autils


class DummyIO(aio.InputOutput):
    def __init__(self):
        # ensure encoding attribute exists
        self.encoding = "utf-8"
        self.errors = []

    def tool_error(self, msg):
        self.errors.append(msg)

    def read_image(self, filename):
        # not used in these tests (we force is_image_file -> False)
        return f"image:{filename}"


def _open_raiser(exc):
    def _raiser(*args, **kwargs):
        raise exc
    return _raiser


@pytest.fixture(autouse=True)
def non_image(monkeypatch):
    # Ensure filename is not detected as an image for these tests
    monkeypatch.setattr(autils, "is_image_file", lambda filename: False)
    yield


def test_read_text_file_not_found_calls_tool_error(monkeypatch):
    monkeypatch.setattr(builtins, "open", _open_raiser(FileNotFoundError()))
    di = DummyIO()
    ret = di.read_text("missing.txt", silent=False)
    assert ret is None
    assert di.errors == ["missing.txt: file not found error"]


def test_read_text_is_directory_calls_tool_error(monkeypatch):
    monkeypatch.setattr(builtins, "open", _open_raiser(IsADirectoryError()))
    di = DummyIO()
    ret = di.read_text("some_dir", silent=False)
    assert ret is None
    assert di.errors == ["some_dir: is a directory"]


def test_read_text_os_error_calls_tool_error(monkeypatch):
    # OSError with a message should be included in the tool_error message
    monkeypatch.setattr(builtins, "open", _open_raiser(OSError("perm")))
    di = DummyIO()
    ret = di.read_text("file.txt", silent=False)
    assert ret is None
    assert len(di.errors) == 1
    assert "file.txt: unable to read: perm" == di.errors[0]


def test_read_text_unicode_error_calls_two_tool_errors(monkeypatch):
    # UnicodeError should produce two tool_error messages
    monkeypatch.setattr(builtins, "open", _open_raiser(UnicodeError("codec")))
    di = DummyIO()
    ret = di.read_text("u.txt", silent=False)
    assert ret is None
    assert len(di.errors) == 2
    assert di.errors[0].startswith("u.txt: ")
    assert "codec" in di.errors[0]
    assert di.errors[1] == "Use --encoding to set the unicode encoding."
