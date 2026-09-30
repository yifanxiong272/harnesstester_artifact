import types
import pytest

from pr_agent.algo import utils
from pr_agent.algo.utils import convert_to_markdown_v2


class DummyGitProvider:
    def __init__(self, link=None):
        self._link = link

    def get_line_link(self, relevant_file, start_line, end_line):
        return self._link or ""


def _patch_common(monkeypatch, *, is_value_no_fn=None, emphasize_fn=None, format_todo_fn=None,
                  process_can_be_split_fn=None, extract_relevant_lines_fn=None, settings=None):
    # Patch get_settings
    if settings is None:
        settings = {"pr_reviewer.enable_intro_text": False}
    monkeypatch.setattr(utils, "get_settings", lambda: settings)

    # Patch is_value_no
    if is_value_no_fn is None:
        monkeypatch.setattr(utils, "is_value_no", lambda v: str(v).strip().lower() in ("no", "false", "none", ""))
    else:
        monkeypatch.setattr(utils, "is_value_no", is_value_no_fn)

    # Patch emphasize_header
    if emphasize_fn is None:
        monkeypatch.setattr(utils, "emphasize_header", lambda text, only_markdown=False, reference_link=None: f"EMPH[{only_markdown}]:{text}")
    else:
        monkeypatch.setattr(utils, "emphasize_header", emphasize_fn)

    # Patch format_todo_items
    if format_todo_fn is None:
        monkeypatch.setattr(utils, "format_todo_items", lambda value, git_provider, gfm_supported: "FORMATTED_TODOS")
    else:
        monkeypatch.setattr(utils, "format_todo_items", format_todo_fn)

    # Patch process_can_be_split
    if process_can_be_split_fn is None:
        monkeypatch.setattr(utils, "process_can_be_split", lambda emoji, value: "CAN_BE_SPLIT")
    else:
        monkeypatch.setattr(utils, "process_can_be_split", process_can_be_split_fn)

    # Patch extract_relevant_lines_str
    if extract_relevant_lines_fn is None:
        monkeypatch.setattr(utils, "extract_relevant_lines_str", lambda end_line, files, relevant_file, start_line, dedent=True: "CODE_SNIPPET")
    else:
        monkeypatch.setattr(utils, "extract_relevant_lines_str", extract_relevant_lines_fn)


def test_generate_full_gfm_markdown_with_incremental_and_issues_round_028(monkeypatch):
    """
    Covers branches for: incremental header, intro text enabled, gfm table path,
    estimated effort numeric path, relevant tests -> no, security concerns with content,
    todo sections non-empty, can be split, and key issues with a valid linked issue
    that returns a details block.
    """
    # Prepare patches
    _patch_common(
        monkeypatch,
        settings={"pr_reviewer.enable_intro_text": True},
        is_value_no_fn=lambda v: str(v).strip().lower() == "no",
    )

    git_provider = DummyGitProvider(link="http://example.com/line")

    # Build output_data exercising many branches
    output_data = {
        "review": {
            # Should be processed as incremental review branch
            "Estimated effort to review [1-5]": "3",
            # Will be converted to lowercase and is_value_no will return True -> 'No relevant tests' branch
            "Relevant tests": "no",
            # Non-empty security concerns -> emphasize_header will be called
            "Security concerns": "There is a secret key here",
            # Non-empty todo sections -> format_todo_items will be called
            "Todo sections": [{"title": "Do X"}],
            # Can be split -> process_can_be_split
            "Can be split": {"some": "thing"},
            # Key issues -> include a valid dict that will result in a reference link + code snippet
            "Key issues to review": [
                None,  # should be skipped without error
                {
                    "relevant_file": "some/file.py",
                    "issue_header": "Possible bug",
                    "issue_content": "This might be wrong",
                    "start_line": 10,
                    "end_line": 12,
                },
            ],
        }
    }

    # Call under test: incremental_review is provided (non-empty) to follow incremental branch
    result = convert_to_markdown_v2(output_data, gfm_supported=True, incremental_review="commit-123",
                                    git_provider=git_provider, files=None)

    # Assertions: check expected fragments to ensure branches were taken
    assert "Review for commits since previous PR-Agent review" in result
    assert "<table>" in result and "</table>" in result
    # Estimated effort row should be present with blue/white bars (blue circle U+1F535)
    assert "Estimated effort to review" in result
    # 'No relevant tests' branch in gfm path should produce 'No relevant tests' strong text
    assert "No relevant tests" in result or "No relevant tests".lower() in result.lower()
    # Security concerns emphasized text
    assert "EMPH[False]:There is a secret key here" in result
    # TODO items formatting inserted
    assert "FORMATTED_TODOS" in result
    # Can be split processed
    assert "CAN_BE_SPLIT" in result
    # The Key issues should have created a details block with a link
    assert "<details><summary><a href='http://example.com/line'" in result


def test_non_gfm_markdown_with_various_edge_cases_round_028(monkeypatch):
    """
    Covers non-gfm branches (gfm_supported=False):
    - no incremental_review -> REGULAR header
    - Estimated effort non-numeric (should be skipped)
    - Relevant tests present (not 'no') -> 'PR contains tests' branch (non-gfm)
    - Security concerns non-empty -> emphasize_header called with only_markdown=True
    - Todo sections non-empty -> format_todo_items used in non-gfm branch
    - Key issues without git_provider -> should format as plain markdown (no link)
    """
    # Patch helpers; emphasize_header must accept only_markdown True
    def emphasize_mock(text, only_markdown=False, reference_link=None):
        return f"EMPH_ONLY_MD[{only_markdown}]:{text}"

    _patch_common(
        monkeypatch,
        settings={"pr_reviewer.enable_intro_text": False},
        is_value_no_fn=lambda v: str(v).strip().lower() == "no",
        emphasize_fn=emphasize_mock,
    )

    # No git provider (None) to ensure branch where reference_link is None
    git_provider = None

    output_data = {
        "review": {
            # Non-numeric estimated effort -> should trigger ValueError branch and be skipped
            "Estimated effort to review [1-5]": "N/A",
            # Relevant tests present -> not 'no'
            "Relevant tests": "yes",
            # Security concerns non-empty
            "Security concerns": "Potential leak",
            # Todo sections non-empty
            "Todo sections": [{"title": "Fix Y"}],
            # Key issues: produce a single valid issue; because git_provider is None,
            # branch will produce non-linked markdown path
            "Key issues to review": [
                {"relevant_file": "a.py", "issue_header": "possible bug", "issue_content": "oops", "start_line": 1, "end_line": 2}
            ],
            # An empty key that should be skipped unless in allowed list
            "Some empty": "",
        }
    }

    result = convert_to_markdown_v2(output_data, gfm_supported=False, incremental_review=None,
                                    git_provider=git_provider, files=None)

    # REGULAR header should appear (non-incremental)
    assert utils.PRReviewHeader.REGULAR.value.split()[0] in result
    # Since gfm_supported is False, there should be markdown headings style like '###' for sections
    assert "###" in result
    # Estimated effort was invalid and should not appear
    assert "Estimated effort to review" not in result
    # Relevant tests non-no should indicate PR contains tests in non-gfm path
    assert "PR contains tests" in result
    # Emphasize header should be called with only_markdown=True in non-gfm security concerns path
    assert "EMPH_ONLY_MD[True]:Potential leak" in result
    # TODO items should be formatted via format_todo_items mock
    assert "FORMATTED_TODOS" in result
    # Key issue without link should produce bold header markdown
    assert "**Possible Issue**" in result or "**possible bug**" in result
