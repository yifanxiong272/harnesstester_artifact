import textwrap
import types
import pr_agent.algo.utils as utils
from pr_agent.algo.utils import extract_relevant_lines_str


class DummyFile:
    def __init__(self, filename, head_file=None, patch=None, language="python"):
        self.filename = filename
        self.head_file = head_file
        self.patch = patch
        self.language = language


class MockLogger:
    def __init__(self):
        self.infos = []
        self.errors = []
        self.exceptions = []

    def info(self, msg):
        self.infos.append(msg)

    def error(self, msg):
        self.errors.append(msg)

    def exception(self, msg):
        self.exceptions.append(msg)


def test_no_files_round_118():
    # When files is falsy, function should return empty string deterministically
    result = extract_relevant_lines_str(end_line=10, files=None, relevant_file="any.py", start_line=1)
    assert result == ""


def test_patch_no_selected_lines_round_118(monkeypatch):
    # When a file has no head_file and extract_hunk_lines_from_patch yields no selected lines,
    # the function logs an error and returns an empty string.
    file = DummyFile(filename="example.py", head_file=None, patch="somepatch", language="python")

    # Patch set_file_languages to return our single dummy file
    monkeypatch.setattr(utils, "set_file_languages", lambda files: [file])

    # Patch extract_hunk_lines_from_patch to return an empty selected_lines
    def fake_extract_hunk_lines_from_patch(patch, filename, start, end, side="right"):
        return (None, "")

    monkeypatch.setattr(utils, "extract_hunk_lines_from_patch", fake_extract_hunk_lines_from_patch)

    # Patch logger to inspect error calls
    mock_logger = MockLogger()
    monkeypatch.setattr(utils, "get_logger", lambda: mock_logger)

    result = extract_relevant_lines_str(end_line=5, files=[file], relevant_file="example.py", start_line=1)

    assert result == ""
    # ensure an error was logged mentioning the filename
    assert any("example.py" in e for e in mock_logger.errors)


def test_patch_with_selected_lines_round_118(monkeypatch):
    # When extract_hunk_lines_from_patch returns selected lines including '+' and '-' prefixes,
    # the function should filter out '-' lines and strip the first char of the others.
    file = DummyFile(filename="script.py", head_file=None, patch="somepatch", language="python")

    monkeypatch.setattr(utils, "set_file_languages", lambda files: [file])

    selected = "+keep_line\n-remove_line\n+keep_line2"

    def fake_extract_hunk_lines_from_patch(patch, filename, start, end, side="right"):
        return (None, selected)

    monkeypatch.setattr(utils, "extract_hunk_lines_from_patch", fake_extract_hunk_lines_from_patch)

    mock_logger = MockLogger()
    monkeypatch.setattr(utils, "get_logger", lambda: mock_logger)

    result = extract_relevant_lines_str(end_line=10, files=[file], relevant_file="script.py", start_line=1)

    # Lines beginning with '-' are removed; '+' lines contribute content without the '+' and with a newline.
    expected_body = "keep_line\nkeep_line2\n"
    expected = f"```{file.language}\n{expected_body}\n```"
    assert result == expected
    # also info should have been called to indicate fallback to patch
    assert any("No content found in file" in i for i in mock_logger.infos)


def test_head_file_with_dedent_round_118(monkeypatch):
    # When head_file exists, the function should extract the requested slice and apply dedent when requested.
    # Use consistent indentation to ensure dedent removes the shared prefix.
    head = "    alpha\n    beta"
    file = DummyFile(filename="dedent.py", head_file=head, patch=None, language="python")

    monkeypatch.setattr(utils, "set_file_languages", lambda files: [file])
    mock_logger = MockLogger()
    monkeypatch.setattr(utils, "get_logger", lambda: mock_logger)

    # Extract both lines and request dedent
    result = extract_relevant_lines_str(end_line=2, files=[file], relevant_file="dedent.py", start_line=1, dedent=True)

    # After dedent, leading spaces should be removed from both lines. The function wraps the result in code fences.
    expected_inner = "alpha\nbeta"
    expected = f"```{file.language}\n{expected_inner}\n```"
    assert result == expected
