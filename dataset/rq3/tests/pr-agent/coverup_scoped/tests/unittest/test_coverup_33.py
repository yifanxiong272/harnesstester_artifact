# file: pr_agent/git_providers/azuredevops_provider.py:379-410
# asked: {"lines": [380, 382, 383, 384, 385, 387, 388, 389, 390, 391, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 407, 408, 409], "branches": [[380, 382], [380, 397], [384, 385], [384, 387], [387, 388], [387, 393], [390, 391], [390, 393], [393, 394], [393, 397]]}
# gained: {"lines": [380, 382, 383, 384, 385, 387, 388, 389, 390, 391, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 407, 408, 409], "branches": [[380, 382], [384, 385], [384, 387], [387, 388], [387, 393], [390, 391], [390, 393], [393, 394], [393, 397]]}

import pytest
from types import SimpleNamespace

import pr_agent.git_providers.azuredevops_provider as mod


class DummyLogger:
    def __init__(self):
        self.warnings = []
        self.exceptions = []

    def warning(self, msg):
        self.warnings.append(msg)

    def exception(self, msg):
        self.exceptions.append(msg)


class DummyGitPullRequest:
    def __init__(self):
        self.title = None
        self.description = None


class FakeClient:
    def __init__(self, raise_on_update=False):
        self.raise_on_update = raise_on_update
        self.last_call = None

    def update_pull_request(self, *args, **kwargs):
        # Capture call for assertions
        self.last_call = {"args": args, "kwargs": kwargs}
        if self.raise_on_update:
            raise Exception("boom")


@pytest.fixture(autouse=True)
def patch_environment(monkeypatch):
    # Ensure provider initialization doesn't raise ImportError
    monkeypatch.setattr(mod, "AZURE_DEVOPS_AVAILABLE", True)

    # Replace GitPullRequest with a simple dummy
    monkeypatch.setattr(mod, "GitPullRequest", DummyGitPullRequest)

    # Make PRDescriptionHeader predictable
    monkeypatch.setattr(
        mod,
        "PRDescriptionHeader",
        SimpleNamespace(FILE_WALKTHROUGH=SimpleNamespace(value="--WALKTHROUGH--")),
    )

    # Use a small max length to force truncation behavior in tests
    monkeypatch.setattr(mod, "MAX_PR_DESCRIPTION_AZURE_LENGTH", 50)

    yield


def setup_provider(monkeypatch, fake_client, logger=None):
    # monkeypatch the provider's _get_azure_devops_client to return our fake client
    def _get_client(self):
        return fake_client, None

    monkeypatch.setattr(mod.AzureDevopsProvider, "_get_azure_devops_client", _get_client)

    # monkeypatch the logger factory
    if logger is None:
        logger = DummyLogger()
    monkeypatch.setattr(mod, "get_logger", lambda: logger)

    # Create provider
    provider = mod.AzureDevopsProvider()
    provider.workspace_slug = "proj"
    provider.repo_slug = "repo"
    provider.pr_num = 123
    return provider, fake_client, logger


def test_publish_description_truncate_at_usage_guide(monkeypatch):
    # Arrange
    fake_client = FakeClient(raise_on_update=False)
    provider, client, logger = setup_provider(monkeypatch, fake_client)

    usage_guide_text = '<details> <summary><strong>✨ Describe tool usage guide:</strong></summary><hr>'

    # Create body such that the usage guide appears after 30 chars -> truncation at that point
    pr_body = "A" * 30 + usage_guide_text + "IGNORED_CONTENT" * 5

    # Act
    provider.publish_description("My Title", pr_body)

    # Assert
    assert client.last_call is not None, "update_pull_request was not called"
    updated = client.last_call["kwargs"]["git_pull_request_to_update"]
    assert isinstance(updated, DummyGitPullRequest)
    assert updated.title == "My Title"
    # Description should be content up to the usage guide (30 A's)
    assert updated.description == "A" * 30
    # No warning should have been logged because truncation brought it under the limit
    assert logger.warnings == []


def test_publish_description_truncate_at_walkthrough(monkeypatch):
    # Arrange
    fake_client = FakeClient(raise_on_update=False)
    provider, client, logger = setup_provider(monkeypatch, fake_client)

    walkthrough_marker = mod.PRDescriptionHeader.FILE_WALKTHROUGH.value
    # Put marker after 30 chars so slicing at marker yields <= MAX, but make total length > MAX
    pr_body = "B" * 30 + walkthrough_marker + "X" * 10  # total length > 50 triggers checks

    # Act
    provider.publish_description("Walk Title", pr_body)

    # Assert
    assert client.last_call is not None
    updated = client.last_call["kwargs"]["git_pull_request_to_update"]
    assert updated.title == "Walk Title"
    # After slicing at the walkthrough marker, description should be the 30 'B's
    assert updated.description == "B" * 30
    # No warning because trimmed to marker under limit
    assert logger.warnings == []


def test_publish_description_final_truncation_and_exception(monkeypatch):
    # Arrange: client will raise to trigger exception logging path
    fake_client = FakeClient(raise_on_update=True)
    provider, client, logger = setup_provider(monkeypatch, fake_client)

    # No markers present; body longer than MAX to force final truncation
    pr_body = "C" * 200

    # Act
    provider.publish_description("Final Title", pr_body)

    # Assert that update_pull_request was attempted and captured prior to raising
    assert client.last_call is not None
    updated = client.last_call["kwargs"]["git_pull_request_to_update"]
    assert updated.title == "Final Title"

    # The description should end with the truncation message
    truncation_message = " ... (description truncated due to length limit)"
    assert updated.description.endswith(truncation_message)
    # And its total length should equal MAX_PR_DESCRIPTION_AZURE_LENGTH
    assert len(updated.description) == mod.MAX_PR_DESCRIPTION_AZURE_LENGTH

    # A warning about truncation should have been logged
    assert any("truncated due to length limit" in w for w in logger.warnings)

    # Exception should have been logged with pr_num and exception text
    assert any(str(provider.pr_num) in e and "boom" in e for e in logger.exceptions)
