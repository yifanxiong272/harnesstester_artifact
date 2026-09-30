import pytest

from pr_agent.git_providers.gitlab_provider import GitLabProvider


class DummyFile:
    def __init__(self, filename, head_file):
        self.filename = filename
        self.head_file = head_file


def make_provider_with_mocks(get_diff_files_callable, send_inline_comment_callable):
    # Create an instance without running __init__ to avoid external side-effects
    provider = object.__new__(GitLabProvider)
    # Attach the mocked methods
    provider.get_diff_files = get_diff_files_callable
    provider.send_inline_comment = send_inline_comment_callable
    return provider


def test_publish_code_suggestions_success_round_052():
    # Prepare a suggestion where original_suggestion exists and a matching file is present
    suggestion = {
        "original_suggestion": {"id": 123},
        "body": "Some text\n```suggestion\nreplacement\n```\nEnd",
        "relevant_file": "path/to/file.py",
        "relevant_lines_start": 2,
        "relevant_lines_end": 4,
    }

    # Dummy file with multiple lines; the relevant line (index 1) should be 'line2'
    dummy_head = "line1\nline2\nline3\nline4"
    dummy_file = DummyFile("path/to/file.py", dummy_head)

    # Mock get_diff_files to return our dummy file
    def _get_diff_files():
        return [dummy_file]

    # Capture the call to send_inline_comment and assert parameters
    calls = []

    def _send_inline_comment(body, edit_type, found, relevant_file, relevant_line_in_file,
                             source_line_no, target_file, target_line_no, original_suggestion):
        calls.append({
            "body": body,
            "edit_type": edit_type,
            "found": found,
            "relevant_file": relevant_file,
            "relevant_line_in_file": relevant_line_in_file,
            "source_line_no": source_line_no,
            "target_file": target_file,
            "target_line_no": target_line_no,
            "original_suggestion": original_suggestion,
        })

    provider = make_provider_with_mocks(_get_diff_files, _send_inline_comment)

    result = provider.publish_code_suggestions([suggestion])

    # Function should return True regardless
    assert result is True

    # Ensure send_inline_comment was called exactly once
    assert len(calls) == 1
    call = calls[0]

    # The range is relevant_lines_end - relevant_lines_start => 4 - 2 = 2
    assert '```suggestion:-0+2' in call["body"]

    # Validate other parameters based on the implementation
    assert call["edit_type"] == 'addition'
    assert call["found"] is True
    assert call["relevant_file"] == "path/to/file.py"
    # relevant_line_in_file should be the second line of dummy_head
    assert call["relevant_line_in_file"] == 'line2'
    assert call["source_line_no"] == -1
    assert call["target_file"] is dummy_file
    # target_line_no = relevant_lines_start + 1 => 3
    assert call["target_line_no"] == 3
    assert call["original_suggestion"] == suggestion["original_suggestion"]


def test_publish_code_suggestions_no_target_file_round_052():
    # Prepare a suggestion whose relevant_file does not match any file returned by get_diff_files
    suggestion = {
        "body": "Example\n```suggestion\nnew\n```",
        "relevant_file": "nonexistent.py",
        "relevant_lines_start": 1,
        "relevant_lines_end": 2,
    }

    # get_diff_files returns a file that does not match suggestion['relevant_file']
    def _get_diff_files():
        return [DummyFile("other_file.py", "a\nb\nc")]

    # If send_inline_comment is called it means the code did not hit the exception path as expected.
    called = {"flag": False}

    def _send_inline_comment(*args, **kwargs):
        called["flag"] = True

    provider = make_provider_with_mocks(_get_diff_files, _send_inline_comment)

    # The code attempts to find a matching file; when none is found it will try to access
    # target_file.head_file and raise AttributeError which should be caught and swallowed.
    result = provider.publish_code_suggestions([suggestion])

    # The function should still return True even if one suggestion failed
    assert result is True

    # send_inline_comment should not have been called because the target file was not found
    assert called["flag"] is False
