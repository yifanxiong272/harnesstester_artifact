# file: pr_agent/algo/utils.py:128-325
# asked: {"lines": [161, 162, 175, 176, 187, 188, 205, 211, 228, 229, 230, 236, 237, 238, 240, 241, 242, 243, 245, 246, 247, 248, 250, 251, 253, 254, 255, 264, 265, 266, 267, 269, 281, 294, 299, 303, 306, 310, 311], "branches": [[158, 161], [166, 169], [174, 175], [175, 176], [175, 177], [202, 205], [208, 211], [225, 228], [233, 236], [239, 240], [240, 241], [240, 250], [242, 243], [242, 245], [250, 251], [250, 253], [257, 173], [263, 264], [264, 265], [264, 269], [280, 281], [291, 294], [297, 303], [298, 299], [305, 306]]}
# gained: {"lines": [161, 162, 187, 188, 205, 228, 229, 230, 240, 241, 242, 245, 246, 247, 248, 281, 294, 299, 303, 306, 310, 311], "branches": [[158, 161], [166, 169], [202, 205], [225, 228], [239, 240], [240, 241], [242, 245], [280, 281], [291, 294], [297, 303], [298, 299], [305, 306]]}

import types
import pytest

from pr_agent.algo import utils as utils_mod
from pr_agent.algo.utils import convert_to_markdown_v2


def test_incremental_intro_and_estimated_effort_and_relevant_tests(monkeypatch):
    # Prepare monkeypatches
    monkeypatch.setattr(utils_mod, "get_settings", lambda: {"pr_reviewer.enable_intro_text": True})

    # Minimal stubs for external dependencies
    monkeypatch.setattr(utils_mod, "is_value_no", lambda v: False)

    # Provide output data that triggers:
    # - incremental header (incremental_review provided)
    # - intro text (get_settings True)
    # - estimated effort numeric path (value '3')
    # - relevant tests branch where is_value_no is False -> "PR contains tests"
    output_data = {
        "review": {
            "todo_summary": "",
            "estimated_effort_to_review_[1-5]": "3",
            "relevant_tests": "yes",
            "score": "10",
        }
    }

    md = convert_to_markdown_v2(output_data, gfm_supported=True, incremental_review="commit-sha-123")
    # Assertions to ensure branches executed
    assert "🔍" in md  # header present (incremental)
    assert "Review for commits since previous PR-Agent review commit-sha-123" in md
    # Estimated effort should display 3 blue bars
    assert "3 🔵" in md or ("🔵🔵🔵" in md and "⚪⚪" in md)
    # Relevant tests should mention PR contains tests
    assert "PR contains tests" in md
    # Score should be present
    assert "Score" in md


def test_estimated_effort_non_numeric_continues(monkeypatch):
    # Keep default settings (intro text off)
    monkeypatch.setattr(utils_mod, "get_settings", lambda: {})
    # Make is_value_no irrelevant here
    monkeypatch.setattr(utils_mod, "is_value_no", lambda v: False)

    # Provide a non-numeric estimated effort that will cause ValueError inside parsing and thus be skipped
    output_data = {
        "review": {
            "todo_summary": "",
            "estimated_effort_to_review_[1-5]": "not-a-number",
            "score": "9",  # ensure there's some output so result isn't empty
        }
    }

    md = convert_to_markdown_v2(output_data, gfm_supported=True, incremental_review=None)
    # The estimated effort label should not appear, but score should
    assert "Estimated effort to review" not in md
    assert "Score" in md


def test_todo_can_be_split_and_security_concerns_gfm(monkeypatch):
    # Configure settings and helpers
    monkeypatch.setattr(utils_mod, "get_settings", lambda: {})
    # is_value_no should treat empty-ish values as 'no' only when appropriate; here return False so branches choose non-empty path
    monkeypatch.setattr(utils_mod, "is_value_no", lambda v: False)

    # Stub helpers used by the function
    monkeypatch.setattr(utils_mod, "format_todo_items", lambda value, gp, gfm: "FORMATTED_TODOS")
    monkeypatch.setattr(utils_mod, "process_can_be_split", lambda emoji, val: "CAN_BE_SPLIT_OUTPUT")
    monkeypatch.setattr(utils_mod, "emphasize_header", lambda txt, only_markdown=False: f"EMPH:{txt}")

    output_data = {
        "review": {
            "todo_summary": "",
            "todo_sections": [{"file": "f1"}],
            "can_be_split": [{"path": "p"}],
            "security_concerns": "Header\nDetails",
        }
    }

    md = convert_to_markdown_v2(output_data, gfm_supported=True, incremental_review=None)
    # Assertions to ensure our stubbed outputs are included
    assert "FORMATTED_TODOS" in md
    assert "CAN_BE_SPLIT_OUTPUT" in md
    assert "Security concerns" in md
    assert "EMPH:Header\nDetails" in md or "EMPH:Header" in md


def test_key_issues_gfm_and_exception_logging(monkeypatch):
    # Prepare settings and stubs
    monkeypatch.setattr(utils_mod, "get_settings", lambda: {})
    # Provide an is_value_no implementation to test both flows
    monkeypatch.setattr(utils_mod, "is_value_no", lambda v: False)

    # Capture logger.exception calls
    logged = {"called": 0, "messages": []}

    class DummyLogger:
        def exception(self, msg):
            logged["called"] += 1
            logged["messages"].append(msg)

    monkeypatch.setattr(utils_mod, "get_logger", lambda: DummyLogger())

    # Stub extract_relevant_lines_str to return content for one issue, and empty for another
    def fake_extract_relevant_lines_str(end_line, files, relevant_file, start_line, dedent=True):
        if relevant_file == "with_lines.py":
            return ">>> relevant lines <<<"
        return ""

    monkeypatch.setattr(utils_mod, "extract_relevant_lines_str", fake_extract_relevant_lines_str)

    # Create a git_provider stub that returns a link for one file
    class GitProviderStub:
        def get_line_link(self, path, start, end):
            return f"http://git/{path}#L{start}-L{end}"

    git_provider = GitProviderStub()

    # Compose issues:
    # - None: should be skipped (covers continue)
    # - good_issue: has link and relevant lines -> should create <details> style entry
    # - no_link_issue: git_provider None for this one (simulate by setting later) -> will go to <strong>... branch
    # - bad_issue: start_line that causes int() to raise and thus be caught and logged
    good_issue = {
        "relevant_file": "with_lines.py",
        "issue_header": "Possible Bug",
        "issue_content": "Something suspicious",
        "start_line": "10",
        "end_line": "12",
    }
    no_link_issue = {
        "relevant_file": "no_link.py",
        "issue_header": "Minor thing",
        "issue_content": "Small note",
        "start_line": "5",
        "end_line": "5",
    }
    bad_issue = {
        "relevant_file": "bad.py",
        "issue_header": "Broken",
        "issue_content": "This will fail",
        "start_line": "not-an-int",
        "end_line": "1",
    }

    output_data = {
        "review": {
            "todo_summary": "",
            "key_issues_to_review": [None, good_issue, no_link_issue, bad_issue],
        }
    }

    # First call with git_provider to exercise path where reference_link exists and relevant_lines_str present
    md_with_git = convert_to_markdown_v2(output_data, gfm_supported=True, incremental_review=None, git_provider=git_provider, files={"with_lines.py": ["line1"]})
    assert "<details><summary><a href='http://git/with_lines.py#L10-L12'><strong>Possible Issue</strong></a>" in md_with_git
    # Ensure the possible bug header was converted to 'Possible Issue'
    assert "Possible Issue" in md_with_git

    # Now call without git_provider to hit branch where reference_link is None for the same data
    md_no_git = convert_to_markdown_v2(output_data, gfm_supported=True, incremental_review=None, git_provider=None, files={})
    # Should include a plain strong header for the issue without link (from no_link_issue)
    assert "<strong>Minor thing</strong><br>Small note" in md_no_git or "Minor thing" in md_no_git

    # Ensure the bad_issue triggered the exception logging (caught by our DummyLogger)
    # The convert_to_markdown_v2 call processes the list and will have attempted to process bad_issue and logged
    assert logged["called"] >= 1
    assert any("Failed to process 'Recommended focus areas for review'" in m or "Failed to process" in m for m in logged["messages"])


def test_key_issues_non_gfm_with_link(monkeypatch):
    # Test the non-gfm (plain markdown) branch where reference_link exists -> should produce markdown link format
    monkeypatch.setattr(utils_mod, "get_settings", lambda: {})
    monkeypatch.setattr(utils_mod, "is_value_no", lambda v: False)

    # Stub extract_relevant_lines_str to return empty so path picks different formatting
    monkeypatch.setattr(utils_mod, "extract_relevant_lines_str", lambda *a, **k: "")

    class GitProviderStub:
        def get_line_link(self, path, start, end):
            return f"https://repo/{path}#L{start}-L{end}"

    git_provider = GitProviderStub()

    issue = {
        "relevant_file": "some.py",
        "issue_header": "Found issue",
        "issue_content": "Details here",
        "start_line": 2,
        "end_line": 4,
    }

    output_data = {
        "review": {
            "todo_summary": "",
            "key_issues_to_review": [issue],
        }
    }

    md = convert_to_markdown_v2(output_data, gfm_supported=False, incremental_review=None, git_provider=git_provider, files={})
    # Expect markdown link style [**Header**](link)
    assert "[**Found issue**](https://repo/some.py#L2-L4)" in md
    assert "Details here" in md
