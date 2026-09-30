import types
import pytest

from pr_agent.git_providers import azuredevops_provider as mod


class FakeLogger:
    def __init__(self):
        self.warnings = []
        self.errors = []

    def warning(self, msg, **kwargs):
        # store message and kwargs for assertions
        self.warnings.append((msg, kwargs))

    def error(self, msg, **kwargs):
        self.errors.append((msg, kwargs))


class FakeClient:
    def __init__(self, raise_on_create=False):
        self.raise_on_create = raise_on_create
        self.calls = []

    def create_thread(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_on_create:
            raise Exception("boom")
        return {"id": 123}


def make_provider_with_client(client):
    # create instance without calling real __init__
    inst = object.__new__(mod.AzureDevopsProvider)
    inst.azure_devops_client = client
    inst.workspace_slug = "workspace"
    inst.repo_slug = "repo"
    inst.pr_num = 42
    return inst


def setup_common(monkeypatch, status_value="closed"):
    # Patch get_settings to return object with azure_devops dict
    fake_settings = types.SimpleNamespace(azure_devops={"default_comment_status": status_value})
    monkeypatch.setattr(mod, "get_settings", lambda: fake_settings)

    # Patch logger
    fake_logger = FakeLogger()
    monkeypatch.setattr(mod, "get_logger", lambda: fake_logger)

    # Provide minimal comment/thread classes expected by the code under test
    class CommentPosition:
        def __init__(self, offset, line):
            self.offset = offset
            self.line = line

    class CommentThreadContext:
        def __init__(self, file_path, right_file_start, right_file_end):
            self.file_path = file_path
            self.right_file_start = right_file_start
            self.right_file_end = right_file_end

    class Comment:
        def __init__(self, content, comment_type):
            self.content = content
            self.comment_type = comment_type

    class CommentThread:
        def __init__(self, comments, thread_context, status):
            self.comments = comments
            self.thread_context = thread_context
            self.status = status

    monkeypatch.setattr(mod, "CommentPosition", CommentPosition)
    monkeypatch.setattr(mod, "CommentThreadContext", CommentThreadContext)
    monkeypatch.setattr(mod, "Comment", Comment)
    monkeypatch.setattr(mod, "CommentThread", CommentThread)

    return fake_logger


def test_publish_code_suggestions_skips_invalid_start_round_095(monkeypatch):
    fake_logger = setup_common(monkeypatch)

    # create provider with fake client that would record calls
    client = FakeClient()
    provider = make_provider_with_client(client)

    # suggestion with invalid start (None) should be skipped
    suggestion = {
        "body": "Fix this",
        "relevant_file": "foo.py",
        "relevant_lines_start": None,
        "relevant_lines_end": 10,
    }

    result = provider.publish_code_suggestions([suggestion])

    assert result is True
    # create_thread should not have been called
    assert client.calls == []
    # logger.warning should have been called mentioning the relevant_lines_start
    assert any("relevant_lines_start is None" in msg for msg, _ in fake_logger.warnings)


def test_publish_code_suggestions_skips_end_before_start_round_095(monkeypatch):
    fake_logger = setup_common(monkeypatch)

    client = FakeClient()
    provider = make_provider_with_client(client)

    # suggestion where end < start should be skipped
    suggestion = {
        "body": "Bad range",
        "relevant_file": "bar.py",
        "relevant_lines_start": 10,
        "relevant_lines_end": 5,
    }

    result = provider.publish_code_suggestions([suggestion])

    assert result is True
    assert client.calls == []
    # logger.warning should include both numbers
    assert any("relevant_lines_end is 5" in msg and "relevant_lines_start is 10" in msg for msg, _ in fake_logger.warnings)


def test_publish_code_suggestions_creates_thread_and_handles_exception_round_095(monkeypatch):
    fake_logger = setup_common(monkeypatch, status_value="open")

    # First: successful create
    client_ok = FakeClient(raise_on_create=False)
    provider_ok = make_provider_with_client(client_ok)

    suggestion_ok = {
        "body": "Apply this change",
        "relevant_file": "baz.py",
        "relevant_lines_start": 1,
        "relevant_lines_end": 3,
    }

    result_ok = provider_ok.publish_code_suggestions([suggestion_ok])

    assert result_ok is True
    # create_thread called exactly once with expected kw names
    assert len(client_ok.calls) == 1
    call_kwargs = client_ok.calls[0]
    # Check that the passed project/repo/pr ids came from the provider attributes
    assert call_kwargs.get("project") == provider_ok.workspace_slug
    assert call_kwargs.get("repository_id") == provider_ok.repo_slug
    assert call_kwargs.get("pull_request_id") == provider_ok.pr_num
    # Check that the comment content propagated into the created thread object
    thread_obj = call_kwargs.get("comment_thread")
    assert thread_obj.status == "open"
    assert thread_obj.comments[0].content == "Apply this change"

    # Second: client raises -> triggers logger.error but function still returns True
    client_bad = FakeClient(raise_on_create=True)
    provider_bad = make_provider_with_client(client_bad)

    suggestion_bad = {
        "body": "Will fail",
        "relevant_file": "qux.py",
        "relevant_lines_start": 2,
        "relevant_lines_end": 4,
    }

    result_bad = provider_bad.publish_code_suggestions([suggestion_bad])

    assert result_bad is True
    # error should have been logged for the failing suggestion
    assert any("Azure failed to publish code suggestion" in msg for msg, _ in fake_logger.errors)
    # ensure the suggestion dict was passed as kwargs to logger.error
    assert any(kwargs.get("suggestion") == suggestion_bad for _, kwargs in fake_logger.errors)
