# file: pr_agent/git_providers/codecommit_client.py:218-277
# asked: {"lines": [242, 243, 245, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 263, 264, 265, 266, 267, 268, 270, 271, 272, 273, 274, 275, 276, 277], "branches": [[242, 243], [242, 245], [248, 249], [248, 263], [271, 272], [271, 273], [273, 274], [273, 275]]}
# gained: {"lines": [242, 243, 245, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 263, 264, 265, 266, 267, 268, 270, 271, 272, 273, 274, 275, 276, 277], "branches": [[242, 243], [248, 249], [248, 263], [271, 272], [271, 273], [273, 274], [273, 275]]}

import pytest
import botocore
from unittest.mock import Mock

from pr_agent.git_providers.codecommit_client import CodeCommitClient


def test_publish_comment_no_annotation_calls_boto(monkeypatch):
    client = CodeCommitClient()

    mock_boto = Mock()
    # Verify post_comment_for_pull_request will be called with no location key
    def fake_connect():
        client.boto_client = mock_boto

    monkeypatch.setattr(client, "_connect_boto_client", fake_connect)

    repo_name = "my-repo"
    pr_number = 42
    dest_commit = "destsha"
    src_commit = "srcsha"
    comment = "hello"

    client.publish_comment(repo_name, pr_number, dest_commit, src_commit, comment)

    # Ensure the boto call was made once
    mock_boto.post_comment_for_pull_request.assert_called_once()
    called_kwargs = mock_boto.post_comment_for_pull_request.call_args.kwargs

    assert called_kwargs["pullRequestId"] == str(pr_number)
    assert called_kwargs["repositoryName"] == repo_name
    assert called_kwargs["beforeCommitId"] == dest_commit
    assert called_kwargs["afterCommitId"] == src_commit
    assert called_kwargs["content"] == comment
    # No 'location' key when no annotation provided
    assert "location" not in called_kwargs


def test_publish_comment_with_annotation_includes_location(monkeypatch):
    client = CodeCommitClient()

    mock_boto = Mock()
    def fake_connect():
        client.boto_client = mock_boto

    monkeypatch.setattr(client, "_connect_boto_client", fake_connect)

    repo_name = "my-repo"
    pr_number = 7
    dest_commit = "d"
    src_commit = "s"
    comment = "annotated"
    annotation_file = "path/to/file.py"
    annotation_line = 123

    client.publish_comment(repo_name, pr_number, dest_commit, src_commit, comment, annotation_file, annotation_line)

    mock_boto.post_comment_for_pull_request.assert_called_once()
    called_kwargs = mock_boto.post_comment_for_pull_request.call_args.kwargs

    assert called_kwargs["pullRequestId"] == str(pr_number)
    assert called_kwargs["repositoryName"] == repo_name
    assert called_kwargs["beforeCommitId"] == dest_commit
    assert called_kwargs["afterCommitId"] == src_commit
    assert called_kwargs["content"] == comment
    # location must be present and contain expected keys/values
    assert "location" in called_kwargs
    location = called_kwargs["location"]
    assert location["filePath"] == annotation_file
    assert location["filePosition"] == annotation_line
    assert location["relativeFileVersion"] == "AFTER"


def _make_client_error(code: str, message: str = "err"):
    return botocore.exceptions.ClientError({"Error": {"Code": code, "Message": message}}, "PostCommentForPullRequest")


@pytest.mark.parametrize(
    "error_code,expected_message_part",
    [
        ("RepositoryDoesNotExistException", "Repository does not exist"),
        ("PullRequestDoesNotExistException", "PR number does not exist"),
        ("SomeOtherException", "Boto3 client error calling post_comment_for_pull_request"),
    ],
)
def test_publish_comment_client_error_variants(monkeypatch, error_code, expected_message_part):
    client = CodeCommitClient()

    mock_boto = Mock()
    # make post_comment_for_pull_request raise the appropriate ClientError
    mock_boto.post_comment_for_pull_request.side_effect = _make_client_error(error_code)

    def fake_connect():
        client.boto_client = mock_boto

    monkeypatch.setattr(client, "_connect_boto_client", fake_connect)

    with pytest.raises(ValueError) as excinfo:
        client.publish_comment("repo", 9, "d", "s", "c")

    assert expected_message_part in str(excinfo.value)


def test_publish_comment_generic_exception_wrapped(monkeypatch):
    client = CodeCommitClient()

    mock_boto = Mock()
    # raise a non-ClientError exception
    mock_boto.post_comment_for_pull_request.side_effect = RuntimeError("boom")

    def fake_connect():
        client.boto_client = mock_boto

    monkeypatch.setattr(client, "_connect_boto_client", fake_connect)

    with pytest.raises(ValueError) as excinfo:
        client.publish_comment("repo", 1, "d", "s", "c")

    assert "Error calling post_comment_for_pull_request" in str(excinfo.value)
