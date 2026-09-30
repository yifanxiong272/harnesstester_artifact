# file: aider/waiting.py:83-97
# asked: {"lines": [86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97], "branches": [[84, 86]]}
# gained: {"lines": [86, 87, 88, 89, 90, 91, 92, 93, 94, 96, 97], "branches": [[84, 86]]}

import sys
import pytest

from aider.waiting import Spinner


class FakeStdoutSuccess:
    def __init__(self):
        self.written = ""
        self.flushed = False

    def isatty(self):
        return True

    def write(self, s):
        # emulate sys.stdout.write behavior
        self.written += s
        return len(s)

    def flush(self):
        self.flushed = True


class FakeStdoutUnicodeError:
    def isatty(self):
        return True

    def write(self, s):
        # raise UnicodeEncodeError to exercise that except branch
        raise UnicodeEncodeError("ascii", b"\xff", 0, 1, "reason")

    def flush(self):
        pass


class FakeStdoutOtherError:
    def isatty(self):
        return True

    def write(self, s):
        raise RuntimeError("boom")

    def flush(self):
        pass


def test_supports_unicode_success(monkeypatch):
    fake = FakeStdoutSuccess()
    monkeypatch.setattr(sys, "stdout", fake)

    spinner = Spinner("testing-success")
    # spinner.unicode_palette is set in __init__ to '░█'
    backspace = "\x08"
    expected = spinner.unicode_palette
    expected += backspace * len(spinner.unicode_palette)
    expected += " " * len(spinner.unicode_palette)
    expected += backspace * len(spinner.unicode_palette)

    # _supports_unicode was called during __init__, so fake.written should match
    assert fake.written == expected
    assert fake.flushed is True

    # In unicode-supporting case, scan_char should be the second char of unicode_palette
    # xlate_from = '=#', so index of '#' is 1
    assert spinner.scan_char == spinner.unicode_palette[1]


def test_supports_unicode_unicodeencodeerror(monkeypatch):
    fake = FakeStdoutUnicodeError()
    monkeypatch.setattr(sys, "stdout", fake)

    spinner = Spinner("testing-unicode-error")
    # If UnicodeEncodeError occurred during _supports_unicode, fallback scan_char is '#'
    assert spinner.scan_char == "#"


def test_supports_unicode_other_exception(monkeypatch):
    fake = FakeStdoutOtherError()
    monkeypatch.setattr(sys, "stdout", fake)

    spinner = Spinner("testing-other-error")
    # Any other exception should also cause fallback to ASCII
    assert spinner.scan_char == "#"
