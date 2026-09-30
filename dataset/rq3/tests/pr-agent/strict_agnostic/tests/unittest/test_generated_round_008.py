import re

import html2text
import pytest

from pr_agent.algo.utils import process_description, PRDescriptionHeader


def test_empty_description_round_008():
    """Empty description should return empty base and empty files list."""
    base, files = process_description("")
    assert base == ""
    assert files == []


def test_process_description_with_files_round_008():
    """A walkthrough using the HTML details summary should be parsed into files.

    This constructs a description that matches the regex branch (the <details><summary><h3>..</h3></summary>
    splitting) and includes a <tr><td> with an inner <details> that matches the file parsing pattern.
    The test asserts that the base description is preserved and that one file dict is returned with
    the expected short/full file names and that the long_summary is normalized to start with '* '.
    """
    header = PRDescriptionHeader.FILE_WALKTHROUGH.value

    # Build a description where the top-level details/summary/h3 pattern is present
    base_text = "Base description text"

    # Inner file details content crafted to match the complex regex used in process_description
    short_name = "short.py"
    short_summary = "summary-code"
    long_filename = "path/to/long_file.py<ul>"  # intentionally ends with '<ul>' to hit the .endswith('<ul>') branch

    # long_summary includes a <li> which the regex expects and uses <br> to be converted by html2text
    long_summary_html = "Line change<br>Another line"

    inner_details = (
        "<details>"
        f"<summary><strong>{short_name}</strong> <dd><code>{short_summary}</code></summary>"
        "<hr>"
        f"{long_filename}"
        f"<li>{long_summary_html}</details>"
    )

    # Put the inner_details inside a table row so re.findall pattern for files will find it
    table_block = "<table>\n<tr><td>" + inner_details + "</td></tr>\n</table>\n\n___\n"

    description_full = (
        base_text
        + "\n"
        + f"<details><summary><h3>{header}</h3></summary>"
        + table_block
        + "end"
    )

    base, files = process_description(description_full)

    # Base should be the initial base_text trimmed
    assert base == base_text

    # One parsed file should be returned
    assert isinstance(files, list)
    assert len(files) == 1

    f0 = files[0]
    # Check that short and full file name were extracted and that '<ul>' was stripped from long file name
    assert f0["short_file_name"] == short_name
    assert f0["short_summary"] == short_summary
    assert f0["full_file_name"] == long_filename[:-4].strip()

    # long_summary is processed through html2text and then prefixed with '* ' when not already list-marked
    assert isinstance(f0["long_summary"], str)
    assert f0["long_summary"].startswith("* ")


def test_process_description_code_ellipsis_round_008():
    """When a file block contains '<code>...</code>' it should be skipped (pass branch).

    This ensures the code path that detects many-files summaries and early-pass is executed.
    """
    header = PRDescriptionHeader.FILE_WALKTHROUGH.value
    base_text = "Intro"

    # Create a file_data that will not match the detailed regexes but contains the special '<code>...</code>'
    inner_details = (
        "<details>"
        "<summary>Not matching pattern</summary>"
        "<hr>"
        "some content <code>...</code> trailing"
        "</details>"
    )

    table_block = "<table>\n<tr><td>" + inner_details + "</td></tr>\n</table>\n\n___\n"

    description_full = (
        base_text
        + "\n"
        + f"<details><summary><h3>{header}</h3></summary>"
        + table_block
    )

    base, files = process_description(description_full)

    # Base should be preserved and files should be empty because the code sees '<code>...</code>' and passes
    assert base == base_text
    assert files == []
