import pytest

from pr_agent.algo import utils
from pr_agent.algo.utils import convert_to_markdown_v2, PRReviewHeader


class DummyGitProvider:
    def __init__(self, link):
        self._link = link

    def get_line_link(self, relevant_file, start_line, end_line):
        return self._link


def test_incremental_and_intro_round_028(monkeypatch):
    """Covers incremental_review header branch and intro text when settings enable it."""
    # Make get_settings return that intro text is enabled
    monkeypatch.setattr(utils, "get_settings", lambda: {"pr_reviewer.enable_intro_text": True})

    output_data = {"review": {"some_key": "some value"}}

    # Call with incremental_review to hit the incremental header branch (lines ~161-162)
    md = convert_to_markdown_v2(output_data=output_data, gfm_supported=True, incremental_review="commit_sha", git_provider=None, files=None)

    # Expect the incremental header marker and the review-for-commits line to be present
    assert PRReviewHeader.INCREMENTAL.value in md
    assert "Review for commits since previous PR-Agent review commit_sha" in md
    # Because get_settings enabled intro text, we also expect the intro observation sentence
    assert "Here are some key observations to aid the review process" in md


def test_relevant_tests_and_todos_round_028(monkeypatch):
    """Covers 'Relevant tests' true/false branches and TODO sections formatting branches.
    Uses monkeypatch to avoid calling other complex helpers.
    """
    # Ensure get_settings does not interfere here
    monkeypatch.setattr(utils, "get_settings", lambda: {})

    # Monkeypatch format_todo_items so behaviour is deterministic
    monkeypatch.setattr(utils, "format_todo_items", lambda value, git_provider, gfm_supported: "TODOITEMS")

    # Case A: gfm_supported True and 'relevant_tests' -> value 'no' should produce 'No relevant tests'
    data_no_tests = {"review": {"relevant_tests": "no", "todo_sections": {}}}
    md_no = convert_to_markdown_v2(output_data=data_no_tests, gfm_supported=True, incremental_review=None, git_provider=None, files=None)
    assert "No relevant tests" in md_no or "No relevant tests" in md_no.replace("&nbsp;", " ")
    # TODOITEMS should be present because format_todo_items returns it for non-empty todo dict (we gave empty dict, so it maps to 'No TODO sections')
    # For explicit coverage, also test non-empty todo value

    data_with_todo = {"review": {"relevant_tests": "yes", "todo_sections": [{"title": "t"}]}}
    md_todo = convert_to_markdown_v2(output_data=data_with_todo, gfm_supported=True, incremental_review=None, git_provider=None, files=None)
    # With our monkeypatched format_todo_items, the TODOITEMS placeholder should appear
    assert "TODOITEMS" in md_todo
    # And for relevant_tests == 'yes' we expect the 'PR contains tests' wording
    assert "PR contains tests" in md_todo

    # Case B: gfm_supported False (plain markdown) and relevant_tests values
    data_no_tests_md = {"review": {"relevant_tests": "no"}}
    md_plain = convert_to_markdown_v2(output_data=data_no_tests_md, gfm_supported=False, incremental_review=None, git_provider=None, files=None)
    assert "No relevant tests" in md_plain

    data_yes_tests_md = {"review": {"relevant_tests": "yes"}}
    md_plain_yes = convert_to_markdown_v2(output_data=data_yes_tests_md, gfm_supported=False, incremental_review=None, git_provider=None, files=None)
    assert "PR contains tests" in md_plain_yes


def test_key_issues_and_reference_links_round_028(monkeypatch):
    """Covers key issues list processing including:
    - skipping invalid entries
    - renaming 'Possible Bug' header
    - branches where a git_provider reference link is present or absent
    - gfm and non-gfm output forms
    """
    monkeypatch.setattr(utils, "get_settings", lambda: {})

    # Ensure extract_relevant_lines_str can be controlled
    monkeypatch.setattr(utils, "extract_relevant_lines_str", lambda end_line, files, relevant_file, start_line, dedent=True: "RELEVANT_CODE")

    # Prepare a list that includes a non-dict (should be skipped) and a valid dict
    issues = [None, {"relevant_file": "f.py", "issue_header": "Possible Bug", "issue_content": "Something is wrong", "start_line": 1, "end_line": 2}]

    # Case 1: gfm_supported True and git_provider returns a non-empty link -> uses <details> path
    gp_with_link = DummyGitProvider("http://example.com/link")
    data = {"review": {"key_issues_to_review": issues}}
    md = convert_to_markdown_v2(output_data=data, gfm_supported=True, incremental_review=None, git_provider=gp_with_link, files={})

    # Should have the HTML details summary with the link and the renamed header 'Possible Issue'
    assert "<details>" in md
    assert "http://example.com/link" in md
    assert "Possible Issue" in md
    assert "RELEVANT_CODE" in md

    # Case 2: gfm_supported True but git_provider returns None or empty -> fallback to plain strong+br form
    gp_no_link = DummyGitProvider("")
    md_no_link = convert_to_markdown_v2(output_data=data, gfm_supported=True, incremental_review=None, git_provider=gp_no_link, files={})
    # When no link is returned, the code builds a <strong>...<br>... string
    assert "<strong>Possible Issue</strong>" in md_no_link or "Possible Issue" in md_no_link

    # Case 3: gfm_supported False and git_provider returns a link -> markdown link formatting path
    md_plain_link = convert_to_markdown_v2(output_data=data, gfm_supported=False, incremental_review=None, git_provider=gp_with_link, files={})
    # Should contain markdown style linked header
    assert "[**Possible Issue**](http://example.com/link)" in md_plain_link


# Ensure tests are discovered/present
if __name__ == "__main__":
    pytest.main([__file__])
