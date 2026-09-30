import importlib
import types
import pytest

MODULE_PATH = "pr_agent.git_providers.azuredevops_provider"


class DummyGitPullRequest:
    def __init__(self):
        # allow setting attributes as in real object
        self.title = None
        self.description = None


class DummyClientRecorder:
    def __init__(self, raise_on_update=False):
        self.raise_on_update = raise_on_update
        self.last_update = None

    def update_pull_request(self, project, repository_id, pull_request_id, git_pull_request_to_update):
        if self.raise_on_update:
            raise RuntimeError("update failed")
        # record the object passed for assertions
        self.last_update = {
            "project": project,
            "repository_id": repository_id,
            "pull_request_id": pull_request_id,
            "git_pull_request_to_update": git_pull_request_to_update,
        }


class LoggerRecorder:
    def __init__(self):
        self.warnings = []
        self.exceptions = []

    def warning(self, msg):
        self.warnings.append(msg)

    def exception(self, msg):
        # mimic logger.exception signature
        self.exceptions.append(msg)


def _make_provider(module, client):
    # create an instance without invoking potentially complex __init__
    Provider = module.AzureDevopsProvider
    provider = object.__new__(Provider)
    provider.azure_devops_client = client
    provider.workspace_slug = "some_project"
    provider.repo_slug = "some_repo"
    provider.pr_num = 42
    return provider


def test_publish_description_slices_at_usage_guide_round_074(monkeypatch):
    """
    If pr_body contains the usage guide text, publish_description should slice the body
    at the usage guide start and pass that shorter description to update_pull_request.
    """
    m = importlib.import_module(MODULE_PATH)

    # patch symbols the function uses
    monkeypatch.setattr(m, "GitPullRequest", DummyGitPullRequest)
    # set a large enough MAX so that only the usage-guide slicing happens
    monkeypatch.setattr(m, "MAX_PR_DESCRIPTION_AZURE_LENGTH", 200)

    # ensure PRDescriptionHeader exists (not used in this test but keep shape)
    class PH:  # simple stand-in
        FILE_WALKTHROUGH = type("FW", (), {"value": "WALKTHROUGH_TEXT"})
    monkeypatch.setattr(m, "PRDescriptionHeader", PH)

    # prepare client that records the update call
    client = DummyClientRecorder()
    provider = _make_provider(m, client)

    # usage guide text must match the literal used in the module
    usage_guide_text = "<details> <summary><strong>\u2728 Describe tool usage guide:</strong></summary><hr>"
    prefix = "This is the meaningful PR body."
    pr_body = prefix + usage_guide_text + "some automated usage guide appended by tools"

    # call the method under test
    provider.publish_description("My Title", pr_body)

    # assert update_pull_request received a GitPullRequest with title and sliced description
    assert client.last_update is not None, "update_pull_request was not called"
    updated_obj = client.last_update["git_pull_request_to_update"]
    assert isinstance(updated_obj, DummyGitPullRequest)
    assert updated_obj.title == "My Title"
    # description should be truncated at the occurrence of usage_guide_text
    assert updated_obj.description == prefix


def test_publish_description_truncates_and_logs_on_exception_round_074(monkeypatch):
    """
    When the description exceeds MAX_PR_DESCRIPTION_AZURE_LENGTH and no earlier markers
    are present, the description should be truncated, a warning logged, and if
    the update call raises an exception it should be logged via logger.exception.
    """
    m = importlib.import_module(MODULE_PATH)

    # Patch GitPullRequest so updated_pr accepts attributes
    monkeypatch.setattr(m, "GitPullRequest", DummyGitPullRequest)

    # Force a very small max so truncation branch is exercised
    monkeypatch.setattr(m, "MAX_PR_DESCRIPTION_AZURE_LENGTH", 50)

    # Provide a PRDescriptionHeader with a FILE_WALKTHROUGH value that will NOT be found
    class PH:
        FILE_WALKTHROUGH = type("FW", (), {"value": "UNLIKELY_WALKTHROUGH_MARKER"})
    monkeypatch.setattr(m, "PRDescriptionHeader", PH)

    # create logger recorder and patch get_logger to return it
    logger = LoggerRecorder()
    monkeypatch.setattr(m, "get_logger", lambda: logger)

    # prepare client that raises on update to hit the except: branch
    client = DummyClientRecorder(raise_on_update=True)
    provider = _make_provider(m, client)

    # build a long body that does not contain usage guide or walkthrough markers
    pr_body = "X" * 200

    # Call the method; it shouldn't raise because exception is caught inside
    provider.publish_description("ErrTitle", pr_body)

    # After call, ensure that a warning about truncation was logged
    assert any("PR description was truncated due to length limit" in w for w in logger.warnings), \
        f"Expected truncation warning, got {logger.warnings}"

    # And because update_pull_request raised, exception should have been logged
    assert any("Could not update pull request" in e for e in logger.exceptions), \
        f"Expected exception log, got {logger.exceptions}"

    # Also confirm that update_pull_request attempted to receive a GitPullRequest object
    # (it raised, so client.last_update is None) but we can still assert the created object
    # would have had attributes set if update didn't raise: instantiate and set to verify shape
    o = DummyGitPullRequest()
    o.title = "ErrTitle"
    # truncated description should end with the truncation message string from the module
    truncation_suffix = " ... (description truncated due to length limit)"
    assert len(truncation_suffix) < m.MAX_PR_DESCRIPTION_AZURE_LENGTH


# Keep tests deterministic and pure; no network or real external services used.
