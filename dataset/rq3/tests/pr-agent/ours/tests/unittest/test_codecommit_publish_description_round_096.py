import pytest
from unittest.mock import Mock
import botocore

from pr_agent.git_providers.codecommit_client import CodeCommitClient


def test_connect_invoked_round_096():
    # When boto_client is None, _connect_boto_client must be called and set boto_client
    client = CodeCommitClient()
    client.boto_client = None

    mock_boto = Mock()
    called = {"connected": False}

    def fake_connect():
        called["connected"] = True
        client.boto_client = mock_boto

    # Patch the instance method directly
    client._connect_boto_client = fake_connect

    # Should not raise
    client.publish_description(123, "title", "body")

    assert called["connected"] is True
    # The mock boto client should have been used to call update functions
    mock_boto.update_pull_request_title.assert_called_once_with(pullRequestId=str(123), title="title")
    mock_boto.update_pull_request_description.assert_called_once_with(pullRequestId=str(123), description="body")


def test_no_connect_when_boto_present_round_096():
    # When boto_client already present, _connect_boto_client should not be invoked
    client = CodeCommitClient()
    mock_boto = Mock()
    client.boto_client = mock_boto

    # Replace connect method with one that would raise if called (ensures it's not called)
    def should_not_be_called():
        raise AssertionError("_connect_boto_client was unexpectedly called")

    client._connect_boto_client = should_not_be_called

    client.publish_description(7, "T", "B")

    mock_boto.update_pull_request_title.assert_called_once_with(pullRequestId=str(7), title="T")
    mock_boto.update_pull_request_description.assert_called_once_with(pullRequestId=str(7), description="B")


@pytest.mark.parametrize("code, expected_text", [
    ("PullRequestDoesNotExistException", "PR number does not exist: 42"),
    ("InvalidTitleException", "Invalid title for PR number: 42"),
    ("InvalidDescriptionException", "Invalid description for PR number: 42"),
    ("PullRequestAlreadyClosedException", "PR is already closed: PR number: 42"),
])
def test_clienterror_specific_codes_raise_valueerror_round_096(code, expected_text):
    client = CodeCommitClient()
    mock_boto = Mock()

    # Make the title update raise the ClientError with specific code
    error_response = {"Error": {"Code": code, "Message": "msg"}}
    exc = botocore.exceptions.ClientError(error_response, "UpdatePullRequest")
    mock_boto.update_pull_request_title.side_effect = exc
    # description shouldn't be called if title fails
    client.boto_client = mock_boto

    with pytest.raises(ValueError) as ei:
        client.publish_description(42, "t", "b")

    assert expected_text in str(ei.value)
    mock_boto.update_pull_request_description.assert_not_called()


def test_other_clienterror_code_raises_generic_valueerror_round_096():
    client = CodeCommitClient()
    mock_boto = Mock()

    # Use an unexpected error code to reach the final ClientError branch
    error_response = {"Error": {"Code": "SomeOtherException", "Message": "msg"}}
    exc = botocore.exceptions.ClientError(error_response, "UpdatePullRequest")
    mock_boto.update_pull_request_title.side_effect = exc
    client.boto_client = mock_boto

    with pytest.raises(ValueError) as ei:
        client.publish_description(99, "t", "b")

    assert "Boto3 client error calling publish_description" in str(ei.value)


def test_non_client_exception_wrapped_round_096():
    client = CodeCommitClient()
    mock_boto = Mock()

    # Raise a generic exception (not ClientError) to trigger the broad except
    mock_boto.update_pull_request_title.side_effect = RuntimeError("boom")
    client.boto_client = mock_boto

    with pytest.raises(ValueError) as ei:
        client.publish_description(5, "t", "b")

    assert "Error calling publish_description" in str(ei.value)
