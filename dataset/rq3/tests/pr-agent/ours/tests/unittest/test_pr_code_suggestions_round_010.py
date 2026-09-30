import types
import pytest
from types import SimpleNamespace

from pr_agent.tools.pr_code_suggestions import PRCodeSuggestions
import pr_agent.tools.pr_code_suggestions as pcs


class FakeComment:
    def __init__(self, body):
        self.body = body


class FakeGitProvider:
    def __init__(self, latest_commit_url, issue_comments=None):
        self._latest_commit_url = latest_commit_url
        self._issue_comments = list(issue_comments or [])
        self.edit_calls = []
        self.published = []
        self.removed = []
        self.edited = []

    def get_latest_commit_url(self):
        return self._latest_commit_url

    def get_issue_comments(self):
        # return iterator as original code does list(git_provider.get_issue_comments())
        return iter(self._issue_comments)

    def get_comment_url(self, comment):
        return f"url-for-{hash(comment.body)}"

    def edit_comment(self, comment, body):
        # record the call
        self.edit_calls.append((comment, body))
        # return a simple marker
        return "edited"

    def remove_comment(self, comment):
        self.removed.append(comment)

    def publish_comment(self, body):
        self.published.append(body)
        return "published-obj"


@pytest.fixture(autouse=True)
def patch_logger_and_settings(monkeypatch):
    # Patch get_logger used by the module to avoid noisy output
    class DummyLogger:
        def info(self, *a, **kw):
            pass

        def exception(self, *a, **kw):
            pass

    monkeypatch.setattr(pcs, "get_logger", lambda: DummyLogger())

    # Provide a minimal get_settings that offers the nested attribute used when only_fold=True
    dummy_settings = SimpleNamespace(pr_code_suggestions=SimpleNamespace(code_suggestions_self_review_text="Self review text"))
    monkeypatch.setattr(pcs, "get_settings", lambda: dummy_settings)

    yield


def test_publish_new_comment_when_no_previous_round_010():
    # Scenario: no previous comments; should publish a new comment using publish_comment
    latest_commit = "https://host/repos/commits/abcdef123456789"
    provider = FakeGitProvider(latest_commit_url=latest_commit, issue_comments=[])

    initial_header = "HEADER"
    pr_comment = f"{initial_header}\nNew suggestion body"

    res = PRCodeSuggestions.publish_persistent_comment_with_history(
        git_provider=provider,
        pr_comment=pr_comment,
        initial_header=initial_header,
        update_header=True,
        name="review",
        final_update_message=True,
        max_previous_comments=1,
        progress_response=None,
        only_fold=False,
    )

    # Expect it returned the object publish_comment returned
    assert res == "published-obj"
    # Ensure publish_comment was called and the created body contains the short commit id
    assert provider.published, "publish_comment not called"
    published_body = provider.published[-1]
    # commit short id is first 7 chars of the final path element
    assert "<!-- abcdef1 -->" in published_body
    # initial_header should be present in the final published body
    assert initial_header in published_body


def test_edit_comment_and_publish_round_010():
    # Scenario: there is a previous comment that starts with initial_header but contains no <table>
    # This triggers edit_comment(comment, pr_comment) and continue; eventually it should publish a new comment
    latest_commit = "https://host/repos/commits/1234567890abcdef"
    # create a comment body that starts with the initial header but has no <table>
    existing_comment = FakeComment("INIT_HDR\nSome old body without table")
    provider = FakeGitProvider(latest_commit_url=latest_commit, issue_comments=[existing_comment])

    initial_header = "INIT_HDR"
    pr_comment = f"{initial_header}\nSuggested content"

    res = PRCodeSuggestions.publish_persistent_comment_with_history(
        git_provider=provider,
        pr_comment=pr_comment,
        initial_header=initial_header,
        update_header=True,
        name="review",
        final_update_message=True,
        max_previous_comments=2,
        progress_response=None,
        only_fold=False,
    )

    # edit_comment should have been called once with the existing comment and original pr_comment
    assert len(provider.edit_calls) == 1
    called_comment, called_body = provider.edit_calls[0]
    assert called_comment is existing_comment
    assert called_body == pr_comment

    # and after loop it should have published a new comment
    assert res == "published-obj"
    assert provider.published
    assert initial_header in provider.published[-1]


def test_progress_response_update_round_010():
    # Scenario: previous comment has a <table> before history header; progress_response provided
    # Should edit progress_response, remove the old comment and return progress_response
    latest_commit = "https://host/repos/commits/feedfacecafebeef"
    # Place an HTML comment before the table so _extract_link picks it up
    header = "OLDHDR"
    html_comment = "<!-- abcdef -->"
    table_html = "<table>row</table>"
    # Compose comment: startswith header, then an HTML comment before the table
    comment_body = f"{header} {html_comment} more text {table_html}"
    existing_comment = FakeComment(comment_body)

    provider = FakeGitProvider(latest_commit_url=latest_commit, issue_comments=[existing_comment])

    initial_header = header
    pr_comment = f"{initial_header}\nNew suggestion table: <table>new</table>"

    progress_response_obj = "progress-obj"

    # Call with a progress_response so the function will call edit_comment(progress_response, pr_comment_updated)
    res = PRCodeSuggestions.publish_persistent_comment_with_history(
        git_provider=provider,
        pr_comment=pr_comment,
        initial_header=initial_header,
        update_header=True,
        name="review",
        final_update_message=True,
        max_previous_comments=3,
        progress_response=progress_response_obj,
        only_fold=False,
    )

    # Should return the progress_response object
    assert res == progress_response_obj

    # The provider.edit_calls should include at least the call editing the progress_response
    # The implementation edits progress_response (the object passed) with the updated pr text
    assert provider.edit_calls, "No edit_comment calls recorded"
    # The last edit should be the one applied to progress_response
    found_progress_edit = any(call[0] == progress_response_obj for call in provider.edit_calls)
    assert found_progress_edit, "progress_response was not updated via edit_comment"

    # The original comment should have been removed
    assert existing_comment in provider.removed

    # Additionally, ensure that the updated body used in edit contains the commit short id marker
    # compute expected short id from latest url
    short_id = latest_commit.split('/')[-1][:7]
    # find the edit that targeted the progress_response and inspect its body argument
    progress_edits = [call for call in provider.edit_calls if call[0] == progress_response_obj]
    assert progress_edits, "progress_response edit not found"
    updated_body = progress_edits[-1][1]
    assert f"<!-- {short_id} -->" in updated_body
