import builtins
import base64
import pytest

from aider.io import InputOutput


def _raise(exc):
    def _r(*a, **k):
        raise exc
    return _r


def test_read_image_oserror_round_140(monkeypatch):
    """When open raises OSError, read_image should call tool_error with the OSError text and return None."""
    io = InputOutput()
    captured = []

    # tool_error replacement that captures the first positional arg (the message)
    io.tool_error = lambda *a, **k: captured.append(a[0] if a else None)

    # Patch builtins.open so any attempt to open raises OSError
    monkeypatch.setattr(builtins, "open", _raise(OSError("boom")))

    result = io.read_image("file.png")

    assert result is None
    assert captured == ["file.png: unable to read: boom"]


def test_read_image_generic_exception_round_140(monkeypatch):
    """When open raises a generic Exception, read_image should call tool_error with the exception text and return None."""
    io = InputOutput()
    captured = []
    io.tool_error = lambda *a, **k: captured.append(a[0] if a else None)

    # Patch builtins.open so it raises a ValueError (caught by the generic Exception handler)
    monkeypatch.setattr(builtins, "open", _raise(ValueError("val_err")))

    result = io.read_image("somefile.jpg")

    assert result is None
    assert captured == ["somefile.jpg: val_err"]


def test_read_image_file_not_found_behaves_as_oserror_round_140(monkeypatch):
    """Although there's a FileNotFoundError handler in source, OSError is caught first.
    Ensure FileNotFoundError ends up being handled by the OSError branch in practice."""
    io = InputOutput()
    captured = []
    io.tool_error = lambda *a, **k: captured.append(a[0] if a else None)

    # FileNotFoundError is a subclass of OSError; confirm OSError branch runs
    monkeypatch.setattr(builtins, "open", _raise(FileNotFoundError("nope")))

    result = io.read_image("missing.png")

    assert result is None
    # Because OSError is the first except, the message should come from that handler
    assert captured == ["missing.png: unable to read: nope"]


def test_read_image_is_a_directory_round_140(monkeypatch):
    """Raising IsADirectoryError should be handled (via OSError in practice) and report a message."""
    io = InputOutput()
    captured = []
    io.tool_error = lambda *a, **k: captured.append(a[0] if a else None)

    monkeypatch.setattr(builtins, "open", _raise(IsADirectoryError("is a dir")))

    result = io.read_image("adir")

    assert result is None
    assert captured == ["adir: unable to read: is a dir"]
