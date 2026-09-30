import importlib
import types
import pytest

import aider.waiting as aw
from aider.waiting import Spinner


class FakeStdout:
    def __init__(self):
        self.written = ""
        self.flushed = 0

    def write(self, s: str):
        # emulate normal successful write
        self.written += s

    def flush(self):
        self.flushed += 1


class RaisingStdout:
    def __init__(self, exc):
        self.exc = exc

    def write(self, s: str):
        raise self.exc

    def flush(self):
        # flush should not be reached when write raises
        raise RuntimeError("flush should not be called")


def make_instance_without_init(unicode_palette, is_tty=True):
    # Create Spinner instance without running its __init__ to keep tests deterministic
    inst = object.__new__(Spinner)
    inst.unicode_palette = unicode_palette
    inst.is_tty = is_tty
    return inst


def test_supports_unicode_writes_expected_sequence_round_139(monkeypatch):
    """
    Exercise the try-success path: stdout.write/flush succeed and method returns True.
    Verify the exact string written to the module's sys.stdout and that flush was called.
    """
    inst = make_instance_without_init("✓")

    fake = FakeStdout()
    # Patch the sys.stdout used by the module under test
    monkeypatch.setattr(aw.sys, "stdout", fake)

    result = inst._supports_unicode()

    # expected sequence: palette + backspaces + spaces + backspaces
    count = len(inst.unicode_palette)
    expected = inst.unicode_palette + "\b" * count + " " * count + "\b" * count

    assert result is True
    assert fake.written == expected
    assert fake.flushed == 1


def test_supports_unicode_handles_unicode_encode_error_round_139(monkeypatch):
    """
    Simulate stdout.write raising UnicodeEncodeError; the method should catch it and return False.
    """
    inst = make_instance_without_init("é")

    # Create an object that raises UnicodeEncodeError on write
    exc = UnicodeEncodeError("ascii", b"", 0, 1, "reason")
    raising = RaisingStdout(exc)

    monkeypatch.setattr(aw.sys, "stdout", raising)

    result = inst._supports_unicode()

    assert result is False


def test_supports_unicode_handles_generic_exception_round_139(monkeypatch):
    """
    Simulate stdout.write raising a generic exception (ValueError) and ensure the method
    catches it and returns False (covers the broad except Exception branch).
    """
    inst = make_instance_without_init("x")

    raising = RaisingStdout(ValueError("boom"))
    monkeypatch.setattr(aw.sys, "stdout", raising)

    result = inst._supports_unicode()

    assert result is False


def test_supports_unicode_respects_is_tty_flag_round_139():
    """
    When is_tty is False, the method should immediately return False and not touch stdout.
    """
    inst = make_instance_without_init("*", is_tty=False)

    # Ensure we don't need to patch stdout here; method should return early
    result = inst._supports_unicode()

    assert result is False
