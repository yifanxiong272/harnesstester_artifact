from types import SimpleNamespace
import pr_agent.git_providers.gitlab_provider as gp
from pr_agent.git_providers.gitlab_provider import GitLabProvider


def test_publish_code_suggestions_success_round_052():
    # Create GitLabProvider instance without running __init__ to avoid external side effects
    provider = object.__new__(GitLabProvider)

    # Prepare a diff file whose filename matches the suggestion and has at least 3 lines
    diff_file = SimpleNamespace(filename="a.txt", head_file="line1\nrelevant_line\nline3")
    provider.get_diff_files = lambda: [diff_file]

    # Capture calls to send_inline_comment
    calls = []

    def fake_send_inline_comment(body, edit_type, found, relevant_file, relevant_line_in_file,
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

    provider.send_inline_comment = fake_send_inline_comment

    # Ensure logger used by the module won't interfere
    class DummyLogger:
        def exception(self, msg):
            # Should not be called in the success path
            raise AssertionError("logger.exception should not be called in success path")

    gp.get_logger = lambda: DummyLogger()

    # Suggestion includes original_suggestion to exercise that branch
    suggestion = {
        "original_suggestion": {"meta": "x"},
        "body": "some code\n```suggestion\nnew code\n```",
        "relevant_file": "a.txt",
        "relevant_lines_start": 2,
        "relevant_lines_end": 3,
    }

    result = provider.publish_code_suggestions([suggestion])

    # The method should return True regardless
    assert result is True

    # send_inline_comment must have been called exactly once
    assert len(calls) == 1
    call = calls[0]

    # The range is relevant_lines_end - relevant_lines_start = 1
    assert "```suggestion:-0+1" in call["body"]

    # Assert the edit metadata set by the implementation
    assert call["edit_type"] == "addition"
    assert call["found"] is True

    # The relevant line extracted must match the second line of head_file
    assert call["relevant_line_in_file"] == "relevant_line"

    # The target_file passed should be the same object we returned from get_diff_files
    assert call["target_file"] is diff_file

    # The target_line_no is relevant_lines_start + 1
    assert call["target_line_no"] == 3


def test_publish_code_suggestions_exception_path_round_052():
    # Create GitLabProvider instance without __init__
    provider = object.__new__(GitLabProvider)

    # Provide a diff file that does NOT match the suggestion filename to force target_file to be None
    diff_file = SimpleNamespace(filename="other.txt", head_file="onlyline")
    provider.get_diff_files = lambda: [diff_file]

    # Replace send_inline_comment with a spy that should not be reached
    provider.send_inline_comment = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("send_inline_comment should not be called when an exception occurs earlier"))

    # Logger spy to capture exception messages
    logged = {"messages": []}

    class SpyLogger:
        def exception(self, msg):
            logged["messages"].append(msg)

    gp.get_logger = lambda: SpyLogger()

    # Suggestion referencing a missing file so target_file remains None and attribute access fails
    suggestion = {
        "body": "something\n```suggestion\nnew\n```",
        "relevant_file": "missing.txt",
        "relevant_lines_start": 1,
        "relevant_lines_end": 2,
    }

    result = provider.publish_code_suggestions([suggestion])

    # The method still returns True at the end
    assert result is True

    # The logger.exception must have been called once with a message containing the hint text
    assert len(logged["messages"]) == 1
    msg = logged["messages"][0]
    assert "Could not publish code suggestion:" in msg
    # Defensive check: ensure suggestion content is present in the logged message
    assert ("missing.txt" in msg) or ("relevant_file" in msg)
