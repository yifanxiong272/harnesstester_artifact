# file: pr_agent/tools/pr_help_docs.py:120-143
# asked: {"lines": [121, 122, 123, 124, 125, 126, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143], "branches": [[123, 124], [123, 138], [128, 129], [128, 130], [130, 131], [130, 133], [138, 139], [138, 140]]}
# gained: {"lines": [121, 122, 123, 124, 125, 126, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143], "branches": [[123, 124], [123, 138], [128, 129], [128, 130], [130, 131], [130, 133], [138, 139], [138, 140]]}

import builtins
import io
import os
import types

import pytest

from pr_agent.tools import pr_help_docs


class LoggerStub:
    def __init__(self):
        self.warnings = []
        self.errors = []
        self.exceptions = []

    def warning(self, msg):
        self.warnings.append(msg)

    def error(self, msg):
        self.errors.append(msg)

    def exception(self, msg):
        self.exceptions.append(msg)


def _make_logger_and_patch(monkeypatch):
    logger = LoggerStub()
    monkeypatch.setattr(pr_help_docs, "get_logger", lambda: logger)
    return logger


def test_map_documentation_files_trimming_skipping_and_read_error(monkeypatch, tmp_path):
    # Prepare files
    good_file = tmp_path / "good.txt"
    good_file.write_text("Hello world\nThis is usable content.")

    long_file = tmp_path / "long.txt"
    long_content = "X" * 200  # letters so will be trimmed when limit < 200
    long_file.write_text(long_content)

    nolett_file = tmp_path / "nolett.txt"
    nolett_file.write_text("1234567890")  # no letters -> should be skipped

    unreadable_file = tmp_path / "unreadable.txt"
    unreadable_file.write_text("This will not be readable by our fake open")

    # Patch builtins.open to raise for unreadable_file only
    real_open = builtins.open

    def fake_open(file, *args, **kwargs):
        # file may be a pathlib.Path or string
        fpath = str(file)
        if os.path.abspath(fpath) == os.path.abspath(str(unreadable_file)):
            raise IOError("simulated read error")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)

    logger = _make_logger_and_patch(monkeypatch)

    # Call with small max length to force trimming
    result = pr_help_docs.map_documentation_files_to_contents(str(tmp_path), [
        str(good_file),
        str(long_file),
        str(nolett_file),
        str(unreadable_file),
    ], max_allowed_file_len=100)

    # Restore builtins.open is handled by monkeypatch fixture automatically

    # Assertions about returned dict
    # Keys are file paths with base_path replaced by ''
    expected_good_key = str(good_file).replace(str(tmp_path), "")
    expected_long_key = str(long_file).replace(str(tmp_path), "")

    assert expected_good_key in result
    assert expected_long_key in result
    assert (str(nolett_file).replace(str(tmp_path), "")) not in result

    # Trimmed long content should have length equal to the limit (100) after strip
    assert len(result[expected_long_key]) == 100

    # Good content preserved and contains expected substring
    assert "Hello world" in result[expected_good_key]

    # Logger should have a warning about trimming and a warning about read error
    assert any("exceeds limit" in msg for msg in logger.warnings), "Expected a trimming warning"
    assert any("Error while reading the file" in msg for msg in logger.warnings), "Expected an error reading warning"

    # No error-level message because we found usable docs
    assert logger.errors == []


def test_no_usable_files_logs_error_and_returns_empty(monkeypatch, tmp_path):
    # Create a file with no letters so it will be skipped
    file_only_digits = tmp_path / "digits.txt"
    file_only_digits.write_text("9876543210")

    logger = _make_logger_and_patch(monkeypatch)

    result = pr_help_docs.map_documentation_files_to_contents(str(tmp_path), [str(file_only_digits)])

    assert result == {}
    # Ensure error was logged about no usable documentation files
    assert any("Couldn't find any usable documentation files" in msg for msg in logger.errors)


def test_outer_exception_is_caught_and_logs_exception(monkeypatch):
    # Create an iterable that raises when iterated to trigger the outer exception handler
    class BadIterable:
        def __iter__(self):
            raise RuntimeError("iteration boom")

    logger = _make_logger_and_patch(monkeypatch)

    result = pr_help_docs.map_documentation_files_to_contents("/some/base", BadIterable())

    assert result == {}
    assert any("Unexpected exception thrown" in msg or "Unexpected exception" in msg for msg in logger.exceptions)
