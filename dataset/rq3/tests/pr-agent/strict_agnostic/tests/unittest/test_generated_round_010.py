import pytest
from pr_agent.tools import pr_code_suggestions as pcs


class FakeComment:
    def __init__(self, body, id=None):
        self.body = body
        self.id = id


class FakeGitProvider:
    def __init__(self, latest_commit_url=None, issue_comments=None):
        # default deterministic commit url
        self._latest_commit_url = latest_commit_url or "http://host/commit/abcdef1234567"
        # list of FakeComment
        self._issue_comments = list(issue_comments) if issue_comments is not None else []

        # records
        self.edited = []  # tuples (comment_or_target, body)
        self.removed = []  # comment
        self.published = []  # bodies
        self.comment_urls = []

    def get_latest_commit_url(self):
        return self._latest_commit_url

    def get_issue_comments(self):
        # emulate an iterator from provider
        return list(self._issue_comments)

    def get_comment_url(self, comment):
        url = f"http://comments/{getattr(comment, 'id', 'unknown')}"
        self.comment_urls.append(url)
        return url

    def edit_comment(self, comment_or_target, body):
        # record the call so tests can assert
        self.edited.append((comment_or_target, body))
        return True

    def remove_comment(self, comment):
        self.removed.append(comment)
        return True

    def publish_comment(self, body):
        self.published.append(body)
        # return an identifiable object so callers can assert
        return {"published": True, "body": body}


def test_publish_persistent_new_comment_round_010():
    """
    When there are no previous comments, the function should publish a new comment
    and include the latest commit short id (first 7 chars) as an HTML comment in the body.
    """
    provider = FakeGitProvider()

    pr_comment = "HEADER\n\nNew suggestions body"
    initial_header = "HEADER"

    result = pcs.PRCodeSuggestions.publish_persistent_comment_with_history(
        git_provider=provider,
        pr_comment=pr_comment,
        initial_header=initial_header,
        update_header=True,
        name="review",
        final_update_message=True,
        max_previous_comments=4,
        progress_response=None,
        only_fold=False,
    )

    # returns the value returned by publish_comment
    assert isinstance(result, dict) and result.get("published") is True
    # publish_comment should have been called once with a body that contains the latest commit short id
    assert len(provider.published) == 1
    published_body = provider.published[0]
    # derive expected latest commit short id from provider
    commit_short = provider.get_latest_commit_url().split('/')[-1][:7]
    assert f"<!-- {commit_short} -->" in published_body
    # ensure the initial header was preserved in the published body structure
    assert initial_header in published_body


def test_publish_persistent_edit_no_table_round_010():
    """
    If an existing comment starts with the initial header but has no <table>, the code
    should call edit_comment on that comment (and then continue). The function should
    then fall back to publishing a new comment.
    """
    # comment body startswith initial_header but lacks a <table>
    existing = FakeComment(body="HEADER some old text", id="c1")
    provider = FakeGitProvider(issue_comments=[existing])

    pr_comment = "HEADER\n\nUpdated suggestions here"
    initial_header = "HEADER"

    result = pcs.PRCodeSuggestions.publish_persistent_comment_with_history(
        git_provider=provider,
        pr_comment=pr_comment,
        initial_header=initial_header,
        update_header=True,
        name="review",
        final_update_message=True,
        max_previous_comments=4,
        progress_response=None,
        only_fold=False,
    )

    # edit_comment should have been called at least once for the existing comment
    assert any(call[0] is existing for call in provider.edited)
    # the body passed to edit_comment should be the new pr_comment (unchanged by function)
    assert any(call[1] == pr_comment for call in provider.edited)
    # and eventually a publish_comment should still have been invoked
    assert len(provider.published) == 1
    # derive expected latest commit short id from provider
    commit_short = provider.get_latest_commit_url().split('/')[-1][:7]
    assert f"<!-- {commit_short} -->" in provider.published[0]


def test_publish_persistent_update_with_progress_response_round_010():
    """
    When an existing comment contains the history section, the function builds an updated
    comment and, if a progress_response is provided, it should edit that progress_response,
    remove the old comment, and return the progress_response object.

    This test crafts a previous comment body that triggers the 'history present' branch,
    ensures the internal _extract_link sees an HTML comment (covering that branch), and
    asserts the provider.edit_comment and remove_comment are called appropriately.
    """
    # Build a previous comment that contains the history header and a latest <table>
    initial_header = "HEADER"
    latest_commit_html = "<!-- abc123 -->"
    # latest part includes a table that will be detected
    latest_table_html = "<table>latest</table>"
    # previous suggestions section containing an older details entry
    prev_history = (
        "\n___\n\n#### Previous suggestions\n"
        "<details><summary>Review up to commit abc000</summary>\n<br><table>old</table>\n\n</details>\n"
    )

    prev_suggestions = (
        f"{initial_header}\n{latest_commit_html}\n\nLatest suggestions up to abc123\n{latest_table_html}\n\n___\n\n"
        + prev_history
    )

    existing = FakeComment(body=prev_suggestions, id="old1")
    provider = FakeGitProvider(issue_comments=[existing])

    # progress response target that should be edited and returned
    progress_response = FakeComment(body="progress placeholder", id="progress1")

    new_pr_comment = f"{initial_header}\n\nA new suggestion table <table>new</table>"

    # set max_previous_comments to 1 to force the branch which removes the oldest suggestion
    returned = pcs.PRCodeSuggestions.publish_persistent_comment_with_history(
        git_provider=provider,
        pr_comment=new_pr_comment,
        initial_header=initial_header,
        update_header=True,
        name="review",
        final_update_message=True,
        max_previous_comments=1,
        progress_response=progress_response,
        only_fold=False,
    )

    # The function should return the progress_response object passed in
    assert returned is progress_response

    # edit_comment should have been called with progress_response and the updated body
    assert any(call[0] is progress_response for call in provider.edited), "progress_response was not edited"
    # ensure remove_comment removed the original comment
    assert existing in provider.removed

    # find the body that was used to edit the progress_response
    edited_bodies = [call[1] for call in provider.edited if call[0] is progress_response]
    assert edited_bodies, "no edited body recorded for progress_response"
    edited_body = edited_bodies[0]

    # The updated body should contain the initial header and the latest commit html comment
    assert initial_header in edited_body
    # The code under test uses git_provider.get_latest_commit_url() to compute the latest commit
    commit_short = provider.get_latest_commit_url().split('/')[-1][:7]
    assert f"<!-- {commit_short} -->" in edited_body
    # The history header should be present in the updated body
    assert "#### Previous suggestions" in edited_body
