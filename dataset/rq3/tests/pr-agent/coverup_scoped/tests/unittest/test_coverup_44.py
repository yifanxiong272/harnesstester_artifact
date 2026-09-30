# file: pr_agent/git_providers/git_provider.py:301-327
# asked: {"lines": [306, 307, 308, 309, 310, 311, 312, 313, 314, 316, 317, 319, 320, 321, 322, 323, 324, 325, 326, 327], "branches": [[308, 309], [308, 327], [309, 308], [309, 310], [312, 313], [312, 316], [320, 321], [320, 323]]}
# gained: {"lines": [306, 307, 308, 309, 310, 311, 312, 313, 314, 316, 317, 319, 320, 321, 322, 323, 324, 325, 326, 327], "branches": [[308, 309], [308, 327], [309, 308], [309, 310], [312, 313], [312, 316], [320, 321], [320, 323]]}

import pytest
from types import SimpleNamespace

from pr_agent.git_providers.git_provider import GitProvider


class DummyProvider(GitProvider):
    def __init__(self, prev_comments=None, latest_commit_url="commit123", comment_url="http://c/1",
                 raise_in_get_issue=False):
        self._prev_comments = prev_comments or []
        self._latest_commit_url = latest_commit_url
        self._comment_url = comment_url
        self.raise_in_get_issue = raise_in_get_issue

        # For test inspection
        self.edits = []
        self.publishes = []

    # Implement abstract methods with minimal behavior

    def is_supported(self, capability: str) -> bool:
        return True

    def get_files(self) -> list:
        return []

    def get_diff_files(self) -> list:
        return []

    def publish_description(self, pr_title: str, pr_body: str):
        # record publish_description calls if needed
        self.publishes.append(("description", pr_title, pr_body))
        return True

    def publish_code_suggestions(self, code_suggestions: list) -> bool:
        self.publishes.append(("code_suggestions", code_suggestions))
        return True

    def get_languages(self):
        return {}

    def get_pr_branch(self):
        return "branch"

    def get_user_id(self):
        return "user"

    def get_pr_description_full(self) -> str:
        return "full description"

    def get_repo_settings(self):
        return {}

    def publish_comment(self, pr_comment: str, is_temporary: bool=False):
        # Record publish calls and return a predictable string
        self.publishes.append(pr_comment)
        return f"PUBLISHED:{pr_comment}"

    def publish_inline_comment(self, body: str, relevant_file: str, relevant_line_in_file: str, original_suggestion=None):
        self.publishes.append(("inline", body, relevant_file, relevant_line_in_file, original_suggestion))
        return True

    def publish_inline_comments(self, comments: list[dict]):
        self.publishes.append(("inline_comments", comments))
        return True

    def remove_initial_comment(self):
        return True

    def remove_comment(self, comment):
        return True

    def get_issue_comments(self):
        if self.raise_in_get_issue:
            raise RuntimeError("boom")
        # Return clones or list as expected
        return list(self._prev_comments)

    def publish_labels(self, labels):
        self.publishes.append(("labels", labels))
        return True

    def get_pr_labels(self, update=False):
        return []

    def add_eyes_reaction(self, issue_comment_id: int, disable_eyes: bool=False):
        return None

    def remove_reaction(self, issue_comment_id: int, reaction_id: int) -> bool:
        return True

    def get_commit_messages(self):
        return []

    # Methods used by publish_persistent_comment_full
    def get_latest_commit_url(self):
        return self._latest_commit_url

    def get_comment_url(self, comment):
        return self._comment_url

    def edit_comment(self, comment, body):
        # Record that an edit was requested
        self.edits.append((comment, body))
        return True


def make_comment(body):
    # Simple comment-like object with a body attribute
    return SimpleNamespace(body=body, id=1)


def test_update_header_and_publish_final_message():
    initial_header = "HEADER"
    # comment whose body starts with the initial header
    comment = make_comment(initial_header + "\nold")
    provider = DummyProvider(prev_comments=[comment], latest_commit_url="deadbeef", comment_url="http://comment/1")

    pr_comment = "HEADER\nThis is the review body."

    result = provider.publish_persistent_comment_full(pr_comment, initial_header, update_header=True,
                                                      name="review", final_update_message=True)

    # It should have edited the comment with the updated header
    assert provider.edits, "edit_comment should have been called"
    edited_comment, edited_body = provider.edits[-1]
    assert edited_comment is comment
    # The updated header should include the latest commit url and capitalized name
    expected_updated_header = f"{initial_header}\n\n#### (Review updated until commit {provider.get_latest_commit_url()})\n"
    assert edited_body.startswith(expected_updated_header)
    # The returned value should be the publish_comment result with the comment URL and latest commit
    expected_publish_message = f"**[Persistent review]({provider.get_comment_url(comment)})** updated to latest commit {provider.get_latest_commit_url()}"
    assert result == f"PUBLISHED:{expected_publish_message}"
    # And publish_comment should have been called with that exact message
    assert provider.publishes and provider.publishes[-1] == expected_publish_message


def test_update_without_changing_header_and_return_comment_when_no_final_message():
    initial_header = "MYHDR"
    comment = make_comment(initial_header + "\nprevious content")
    provider = DummyProvider(prev_comments=[comment], latest_commit_url="xyz", comment_url="http://c/2")

    pr_comment = "MYHDR\nKeep header as-is."

    # update_header=False so pr_comment should be used as-is for edit; final_update_message=False so method returns the comment
    result = provider.publish_persistent_comment_full(pr_comment, initial_header, update_header=False,
                                                      name="review", final_update_message=False)

    # Should have edited with the original pr_comment unchanged
    assert provider.edits, "edit_comment should have been called"
    edited_comment, edited_body = provider.edits[-1]
    assert edited_comment is comment
    assert edited_body == pr_comment
    # Should return the original comment object
    assert result is comment
    # Should not have published a final message
    # (publish_comment is not called because final_update_message=False)
    assert all(not isinstance(p, str) or not p.startswith("**[Persistent") for p in provider.publishes)


def test_no_matching_previous_comment_publishes_new_comment():
    initial_header = "SOMEHEADER"
    # previous comment does NOT start with the header
    comment = make_comment("OTHERHEADER\nsomething")
    provider = DummyProvider(prev_comments=[comment])

    pr_comment = "SOMEHEADER\nNew persistent comment."

    result = provider.publish_persistent_comment_full(pr_comment, initial_header, update_header=True,
                                                      name="review", final_update_message=True)

    # Since no previous comment started with initial_header, publish_comment should be called with the original pr_comment
    assert provider.publishes, "publish_comment should have been called"
    assert provider.publishes[-1] == pr_comment
    assert result == f"PUBLISHED:{pr_comment}"
    # No edit should have been attempted
    assert not provider.edits


def test_exception_in_get_issue_comments_logs_and_publishes():
    initial_header = "H"
    # Make a provider that raises when fetching issue comments
    provider = DummyProvider(raise_in_get_issue=True)

    pr_comment = "H\nShould be published despite exception."

    # Call should catch the exception and still call publish_comment
    result = provider.publish_persistent_comment_full(pr_comment, initial_header)

    assert provider.publishes, "publish_comment should have been called even after exception"
    assert provider.publishes[-1] == pr_comment
    assert result == f"PUBLISHED:{pr_comment}"
