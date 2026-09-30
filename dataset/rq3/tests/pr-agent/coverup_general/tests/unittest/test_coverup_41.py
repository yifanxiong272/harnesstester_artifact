# file: pr_agent/tools/pr_help_docs.py:120-143
# asked: {"lines": [121, 122, 123, 124, 125, 126, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143], "branches": [[123, 124], [123, 138], [128, 129], [128, 130], [130, 131], [130, 133], [138, 139], [138, 140]]}
# gained: {"lines": [121, 122, 123, 124, 125, 126, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143], "branches": [[123, 124], [123, 138], [128, 129], [128, 130], [130, 131], [130, 133], [138, 139], [138, 140]]}

import os
import types
import pytest

import pr_agent.tools.pr_help_docs as pr_help_docs


class MockLogger:
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


def test_skip_non_alpha_logs_error(monkeypatch, tmp_path):
    # Create a file with no alphabetic characters
    file_path = tmp_path / "numbers.txt"
    file_path.write_text("12345 67890\n", encoding="utf-8")

    mock_logger = MockLogger()
    # Patch the module-level get_logger to return our mock logger
    monkeypatch.setattr(pr_help_docs, "get_logger", lambda: mock_logger)

    result = pr_help_docs.map_documentation_files_to_contents(str(tmp_path), [str(file_path)])
    # Should be empty dict because file contains no alphabetic characters
    assert result == {}
    # Should have logged an error about not finding any usable documentation files
    assert any("Couldn't find any usable documentation files" in e for e in mock_logger.errors)


def test_trim_and_warning_and_key(monkeypatch, tmp_path):
    # Create a file with alphabetic content longer than allowed
    file_path = tmp_path / "long.txt"
    long_content = "a" * 150
    file_path.write_text(long_content, encoding="utf-8")

    mock_logger = MockLogger()
    monkeypatch.setattr(pr_help_docs, "get_logger", lambda: mock_logger)

    # Use a small max_allowed_file_len to force trimming
    max_len = 100
    result = pr_help_docs.map_documentation_files_to_contents(str(tmp_path), [str(file_path)], max_allowed_file_len=max_len)

    # Should have one entry
    assert isinstance(result, dict)
    assert len(result) == 1
    # Key should correspond to the file path with base_path removed
    key = next(iter(result.keys()))
    assert key.endswith("long.txt")
    # Value should be trimmed to max_len
    value = next(iter(result.values()))
    assert len(value) == max_len
    assert value == long_content[:max_len]
    # Should have logged a warning about trimming
    assert any("exceeds limit" in w for w in mock_logger.warnings)


def test_handles_file_open_error_and_continues(monkeypatch, tmp_path):
    # Create one valid file and one invalid path
    good_file = tmp_path / "good.md"
    good_file.write_text("This is fine.", encoding="utf-8")
    bad_file = tmp_path / "does_not_exist.md"
    # Ensure bad_file does not exist
    if bad_file.exists():
        if bad_file.is_file():
            bad_file.unlink()
        else:
            # if directory, remove
            os.rmdir(bad_file)

    mock_logger = MockLogger()
    monkeypatch.setattr(pr_help_docs, "get_logger", lambda: mock_logger)

    doc_files = [str(bad_file), str(good_file)]
    result = pr_help_docs.map_documentation_files_to_contents(str(tmp_path), doc_files)

    # Good file should be in result, bad file should be skipped
    assert any("good.md" in k for k in result.keys())
    assert any("This is fine." in v for v in result.values())
    # Warning should have been logged for the bad file
    assert any("Error while reading the file" in w for w in mock_logger.warnings)
    # No overall error should be logged because we found a usable file
    assert mock_logger.errors == []


def test_outer_exception_returns_empty_and_logs_exception(monkeypatch):
    # Create an object whose __iter__ raises to trigger the outer exception block
    class BadIterable:
        def __iter__(self):
            raise RuntimeError("iterator boom")

    mock_logger = MockLogger()
    monkeypatch.setattr(pr_help_docs, "get_logger", lambda: mock_logger)

    # Call with the BadIterable; should be caught by the outer try/except
    result = pr_help_docs.map_documentation_files_to_contents("/base/path", BadIterable())
    assert result == {}
    # exception should have been logged
    assert any("Unexpected exception thrown" in e for e in mock_logger.exceptions)
