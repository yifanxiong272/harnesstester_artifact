import os
import builtins
from tempfile import TemporaryDirectory
import pr_agent.tools.pr_help_docs as phm
from pr_agent.tools.pr_help_docs import map_documentation_files_to_contents


class FakeLogger:
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


def test_non_alpha_files_and_empty_result_round_082(monkeypatch):
    """A file that contains no alphabetic characters should be skipped,
    and when nothing usable is found the function should log an error and
    return an empty dict.
    """
    fake_logger = FakeLogger()
    # Patch the module-level get_logger to return our fake logger
    monkeypatch.setattr(phm, "get_logger", lambda: fake_logger)

    with TemporaryDirectory() as td:
        base_path = td
        fn = os.path.join(td, "numbers.txt")
        with open(fn, "w", encoding="utf-8") as f:
            f.write("1234567890 0987654321")

        result = map_documentation_files_to_contents(base_path, [fn])

    # No usable files -> empty dict and an error logged
    assert result == {}
    assert any("Couldn't find any usable documentation files" in e for e in fake_logger.errors)


def test_trim_and_preserve_path_round_082(monkeypatch):
    """A file exceeding max_allowed_file_len should be trimmed and stored
    under a path with the base_path removed.
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(phm, "get_logger", lambda: fake_logger)

    with TemporaryDirectory() as td:
        base_path = td
        fn = os.path.join(td, "readme.md")
        content = "a" * 25 + " end"
        with open(fn, "w", encoding="utf-8") as f:
            f.write(content)

        # Trim to 10 chars
        result = map_documentation_files_to_contents(base_path, [fn], max_allowed_file_len=10)

    # Key should be the file path with base_path removed
    expected_key = str(fn).replace(str(base_path), "")
    assert expected_key in result
    # Content stored should be trimmed to the limit
    assert len(result[expected_key]) == 10
    # A warning about trimming should have been logged
    assert any("exceeds limit" in w for w in fake_logger.warnings)


def test_file_read_exception_hits_warning_round_082(monkeypatch):
    """If open raises while reading a file, the inner except should log a warning
    and the file should be skipped, eventually leading to an empty result
    and an error logged for no usable files.
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(phm, "get_logger", lambda: fake_logger)

    # Replace the module's open with one that always raises for this test
    def fake_open_raising(file, mode="r", encoding=None):
        raise OSError("boom")

    monkeypatch.setattr(phm, "open", fake_open_raising)

    with TemporaryDirectory() as td:
        base_path = td
        fn = os.path.join(td, "will_fail.md")
        # We don't actually create the file because open is patched to raise
        result = map_documentation_files_to_contents(base_path, [fn])

    # Should return empty dict when all files fail to be read
    assert result == {}
    # Inner read error should produce a warning
    assert any("Error while reading the file" in w for w in fake_logger.warnings)
    # Because nothing usable, an error is logged as well
    assert any("Couldn't find any usable documentation files" in e for e in fake_logger.errors)


def test_outer_exception_round_082(monkeypatch):
    """If iterating over doc_files raises, the outer exception handler should
    be triggered, logging an exception and returning an empty dict.
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(phm, "get_logger", lambda: fake_logger)

    class BrokenIterable:
        def __iter__(self):
            raise RuntimeError("iteration failed")

    result = map_documentation_files_to_contents("/irrelevant/base", BrokenIterable())

    assert result == {}
    assert any("Unexpected exception thrown" in e or fake_logger.exceptions for e in ["dummy"]) is True or len(fake_logger.exceptions) >= 0
    # The function uses get_logger().exception(...) in the outer except; ensure it was called
    assert len(fake_logger.exceptions) >= 1
