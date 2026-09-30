import re
from types import SimpleNamespace
import pr_agent.algo.utils as utils


class FakeLogger:
    def __init__(self):
        self.debug_calls = []
        self.warning_calls = []
        self.error_calls = []
        self.exception_calls = []

    def debug(self, *args, **kwargs):
        self.debug_calls.append((args, kwargs))

    def warning(self, *args, **kwargs):
        self.warning_calls.append((args, kwargs))

    def error(self, *args, **kwargs):
        self.error_calls.append((args, kwargs))

    def exception(self, *args, **kwargs):
        self.exception_calls.append((args, kwargs))


class FakeHTML2Text:
    def __init__(self):
        # matched usage in code: set body_width = 0
        self.body_width = None

    def handle(self, text: str) -> str:
        # Keep transformation deterministic and simple: return input as-is
        return text


def test_parse_single_file_entry_round_008(monkeypatch):
    """
    Verify process_description extracts one file entry from a markdown/html walkthrough table.
    Covers branches where: marker present, table end detected with '</table>\n\n___',
    a details block matches regex -> groups are extracted, long_filename ends with '<ul>' trimmed,
    long_summary starts with '\\-' and is converted to list item starting with '* '
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(utils, "get_logger", lambda: fake_logger)
    # Ensure html2text.HTML2Text in utils resolves to our fake
    monkeypatch.setattr(utils.html2text, "HTML2Text", FakeHTML2Text)

    # Patch the header marker used by the function by replacing the module-level symbol
    marker = "[FILE_WALK]"
    # Replace the entire PRDescriptionHeader in the utils module with a simple namespace that has the same shape
    monkeypatch.setattr(utils, "PRDescriptionHeader", SimpleNamespace(FILE_WALKTHROUGH=SimpleNamespace(value=marker)))

    # Build a description where group(3) (long filename) ends with '<ul>' and group(4) (long summary)
    # starts with a backslash-hyphen sequence (literal '\-') so code converts to '* ' prefix
    short_name = "short.txt"
    short_summary = "short-summary"
    long_filename_with_ul = "path/to/full_name.txt<ul>"
    long_summary_raw = "\\-Long<br>content"  # after replacements this will start with '\-' and get converted

    details = (
        "<details>"
        f"<summary><strong>{short_name}</strong><dd><code>{short_summary}</code></summary>"
        "<hr>"
        f"{long_filename_with_ul} <li> {long_summary_raw}"
        "</details>"
    )

    table = f"<table>\n<tr><td>{details}</td></tr>\n</table>\n\n___"
    description_full = f"Intro text {marker} {table}"

    base, files = utils.process_description(description_full)

    # Base should be the portion before the marker (strip applied)
    assert base.strip().startswith("Intro text")
    assert isinstance(files, list)
    assert len(files) == 1
    file_info = files[0]

    # Validate extracted pieces
    assert file_info["short_file_name"] == short_name
    # long filename should have the trailing '<ul>' removed
    assert file_info["full_file_name"] == "path/to/full_name.txt"
    assert file_info["short_summary"] == short_summary
    # long summary should be converted: leading '\-' => '* ' + remainder, and '<br>' removed
    # Accept small formatting variance produced by html2text.handle
    assert file_info["long_summary"].startswith("*")
    assert "Long" in file_info["long_summary"]

    # No unexpected warnings/errors should have been emitted for the successful parse of our well-formed entry
    assert not fake_logger.error_calls
    assert not fake_logger.exception_calls


def test_unparseable_file_emits_warning_round_008(monkeypatch):
    """
    Verify that an unparseable <details> block (no matching regex and no '<code>...</code>') leads to a warning.
    Covers branch that triggers get_logger().warning for failed parse (line around 1414).
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(utils, "get_logger", lambda: fake_logger)
    monkeypatch.setattr(utils.html2text, "HTML2Text", FakeHTML2Text)

    marker = "[FILE_WALK]"
    # Replace PRDescriptionHeader at module level to avoid Enum reassignment
    monkeypatch.setattr(utils, "PRDescriptionHeader", SimpleNamespace(FILE_WALKTHROUGH=SimpleNamespace(value=marker)))

    # details content that won't match inner regex and won't contain '<code>...</code>'
    bad_details = "<details><summary>no-match</summary><hr>some random content without expected separators</details>"
    table = f"<table>\n<tr><td>{bad_details}</td></tr>\n</table>\n\n___"
    description_full = f"Base before marker {marker} {table}"

    base, files = utils.process_description(description_full)

    # Should return base and an empty files list since parsing failed for the details entry
    assert base.strip().startswith("Base before marker")
    assert files == []

    # There should be at least one warning call mentioning failed to parse description
    found_warning = any("Failed to parse description" in (args[0] if args else "") or ("Failed to parse description" in str((kwargs.get('artifact') or {}).get('description', ''))) for args, kwargs in fake_logger.warning_calls)
    assert fake_logger.warning_calls and found_warning
