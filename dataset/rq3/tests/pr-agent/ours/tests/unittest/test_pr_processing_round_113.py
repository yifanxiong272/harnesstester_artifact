import pytest

import pr_agent.algo.pr_processing as pr_processing
from pr_agent.algo.pr_processing import add_ai_metadata_to_diff_files


class MockLogger:
    def __init__(self):
        self.warnings = []
        self.errors = []

    def warning(self, msg):
        self.warnings.append(msg)

    def error(self, msg, artifact=None):
        # accept both positional and keyword artifact
        self.errors.append((msg, artifact))


class DummyDiffFile:
    def __init__(self, filename: str):
        self.filename = filename
        self.ai_file_summary = None


class DummyGitProvider:
    def __init__(self, diff_files):
        self._diff_files = diff_files

    def get_diff_files(self):
        return self._diff_files


def test_empty_pr_description_files_round_113(monkeypatch):
    """
    When pr_description_files is falsy, the function should log a warning and return early.
    """
    logger = MockLogger()
    monkeypatch.setattr(pr_processing, "get_logger", lambda: logger)

    gp = DummyGitProvider([])

    # Call with empty list -> should trigger the early return path
    result = add_ai_metadata_to_diff_files(gp, [])

    # function returns None and warning was captured
    assert result is None
    assert any("PR description files are empty." in w for w in logger.warnings)


def test_matching_files_round_113(monkeypatch):
    """
    If diff files contain filenames matching pr_description_files['full_file_name'],
    those diff file objects should receive ai_file_summary set to the corresponding dict.
    """
    logger = MockLogger()
    monkeypatch.setattr(pr_processing, "get_logger", lambda: logger)

    # prepare pr description files and a diff file whose filename has surrounding whitespace
    pr_desc = [{"full_file_name": "file1.txt", "ai_summary": "summary1"}]
    diff_file = DummyDiffFile(" file1.txt ")
    gp = DummyGitProvider([diff_file])

    add_ai_metadata_to_diff_files(gp, pr_desc)

    # ai_file_summary should be assigned the exact dict from pr_desc
    assert diff_file.ai_file_summary is pr_desc[0]
    # no errors should have been logged for this successful match
    assert logger.errors == []


def test_no_matching_files_logs_error_round_113(monkeypatch):
    """
    When no filenames match between diff files and pr description files, the function should log an error
    with an artifact containing the original pr_description_files.
    """
    logger = MockLogger()
    monkeypatch.setattr(pr_processing, "get_logger", lambda: logger)

    pr_desc = [{"full_file_name": "fileA.txt", "ai_summary": "sA"}]
    # diff file that won't match
    diff_file = DummyDiffFile("other_file.txt")
    gp = DummyGitProvider([diff_file])

    add_ai_metadata_to_diff_files(gp, pr_desc)

    # Should have logged an error about failing to find any matches
    assert any("Failed to find any matching files between PR description and diff files." in msg for msg, _ in logger.errors)

    # The artifact passed to the logger.error should contain the original pr_description_files
    found = False
    for msg, artifact in logger.errors:
        if artifact and isinstance(artifact, dict) and artifact.get("pr_description_files") is pr_desc:
            found = True
    assert found, "Expected artifact with original pr_description_files to be logged"


def test_exception_logs_traceback_round_113(monkeypatch):
    """
    If git_provider.get_diff_files raises, the exception should be caught and an error logged with a traceback artifact.
    """
    logger = MockLogger()
    monkeypatch.setattr(pr_processing, "get_logger", lambda: logger)

    class BrokenGitProvider:
        def get_diff_files(self):
            raise ValueError("boom")

    gp = BrokenGitProvider()

    # Call and ensure exception is handled inside function (no exception escapes)
    add_ai_metadata_to_diff_files(gp, [{"full_file_name": "irrelevant.txt"}])

    # Check that an error was logged including the exception message
    assert any("Failed to add AI metadata to diff files" in msg for msg, _ in logger.errors)

    # Ensure the artifact contains a traceback string
    tb_found = False
    for msg, artifact in logger.errors:
        if artifact and isinstance(artifact, dict) and "traceback" in artifact:
            if isinstance(artifact["traceback"], str) and artifact["traceback"].strip():
                tb_found = True
    assert tb_found, "Expected traceback string in logged artifact"
