# file: pr_agent/git_providers/azuredevops_provider.py:57-95
# asked: {"lines": [61, 62, 63, 64, 65, 66, 67, 69, 70, 71, 72, 74, 75, 76, 77, 78, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 93, 94, 95], "branches": [[63, 64], [63, 95], [69, 70], [69, 74], [74, 75], [74, 80]]}
# gained: {"lines": [61, 62, 63, 64, 65, 66, 67, 69, 70, 71, 72, 74, 75, 76, 77, 78, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 93, 94, 95], "branches": [[63, 64], [63, 95], [69, 70], [69, 74], [74, 75], [74, 80]]}

import pytest

import pr_agent.git_providers.azuredevops_provider as azure_mod


class FakeLogger:
    def __init__(self):
        self.warnings = []
        self.errors = []

    def warning(self, msg, *args, **kwargs):
        self.warnings.append((msg, args, kwargs))

    def error(self, msg, *args, **kwargs):
        self.errors.append((msg, args, kwargs))


class FakeSettings:
    def __init__(self, azure_devops):
        self.azure_devops = azure_devops


class FakeComment:
    def __init__(self, content=None, comment_type=None):
        self.content = content
        self.comment_type = comment_type


class FakeCommentPosition:
    def __init__(self, offset=None, line=None):
        self.offset = offset
        self.line = line


class FakeCommentThreadContext:
    def __init__(self, file_path=None, right_file_start=None, right_file_end=None):
        self.file_path = file_path
        self.right_file_start = right_file_start
        self.right_file_end = right_file_end


class FakeCommentThread:
    def __init__(self, comments=None, thread_context=None, status=None):
        self.comments = comments
        self.thread_context = thread_context
        self.status = status


def setup_common(monkeypatch, logger=None, settings_dict=None):
    # Prevent AzureDevopsProvider from trying to create real clients during __init__
    monkeypatch.setattr(azure_mod.AzureDevopsProvider, "_get_azure_devops_client", lambda self: (None, None))
    # Provide fake get_logger and get_settings within the azure_mod module (they were imported at module import)
    if logger is None:
        logger = FakeLogger()
    monkeypatch.setattr(azure_mod, "get_logger", lambda: logger)
    if settings_dict is None:
        settings_dict = {"default_comment_status": "closed"}
    # Provide minimal azure_devops dict so get_settings().azure_devops[...] access works
    monkeypatch.setattr(azure_mod, "get_settings", lambda: FakeSettings({"default_comment_status": settings_dict["default_comment_status"], "org": settings_dict.get("org"), "pat": settings_dict.get("pat")}))
    # monkeypatch azure devops classes used in the module to avoid importing real azure classes
    monkeypatch.setattr(azure_mod, "Comment", FakeComment)
    monkeypatch.setattr(azure_mod, "CommentPosition", FakeCommentPosition)
    monkeypatch.setattr(azure_mod, "CommentThreadContext", FakeCommentThreadContext)
    monkeypatch.setattr(azure_mod, "CommentThread", FakeCommentThread)
    return logger


def test_publish_code_suggestions_skips_when_start_invalid(monkeypatch):
    logger = setup_common(monkeypatch)

    provider = azure_mod.AzureDevopsProvider()
    # set minimal attributes used in method
    provider.azure_devops_client = None  # shouldn't be called
    provider.workspace_slug = "proj"
    provider.repo_slug = "repo"
    provider.pr_num = 1

    suggestions = [
        {
            "body": "no start",
            "relevant_file": "f.py",
            "relevant_lines_start": -1,  # triggers the first continue branch (lines 69-72)
            "relevant_lines_end": 10,
        }
    ]

    result = provider.publish_code_suggestions(suggestions)
    assert result is True
    # ensure warning was logged about relevant_lines_start
    assert any("relevant_lines_start is -1" in entry[0] for entry in logger.warnings)


def test_publish_code_suggestions_skips_when_end_less_than_start(monkeypatch):
    logger = setup_common(monkeypatch)

    provider = azure_mod.AzureDevopsProvider()
    provider.azure_devops_client = None  # shouldn't be called
    provider.workspace_slug = "proj"
    provider.repo_slug = "repo"
    provider.pr_num = 2

    suggestions = [
        {
            "body": "bad range",
            "relevant_file": "f.py",
            "relevant_lines_start": 10,
            "relevant_lines_end": 5,  # triggers the second continue branch (lines 74-78)
        }
    ]

    result = provider.publish_code_suggestions(suggestions)
    assert result is True
    # ensure warning was logged mentioning both values
    assert any("relevant_lines_end is 5" in entry[0] and "relevant_lines_start is 10" in entry[0] for entry in logger.warnings)


def test_publish_code_suggestions_creates_thread_success(monkeypatch):
    logger = setup_common(monkeypatch, settings_dict={"default_comment_status": "open", "org": "o", "pat": "p"})

    calls = []

    class FakeClient:
        def create_thread(self, comment_thread=None, project=None, repository_id=None, pull_request_id=None):
            # record call for assertions
            calls.append({
                "comment_thread": comment_thread,
                "project": project,
                "repository_id": repository_id,
                "pull_request_id": pull_request_id,
            })
            return {"status": "ok"}

    provider = azure_mod.AzureDevopsProvider()
    provider.azure_devops_client = FakeClient()
    provider.workspace_slug = "my_project"
    provider.repo_slug = "my_repo"
    provider.pr_num = 123

    suggestions = [
        {
            "body": "please change this",
            "relevant_file": "path/to/file.py",
            "relevant_lines_start": 3,
            "relevant_lines_end": 4,
        }
    ]

    result = provider.publish_code_suggestions(suggestions)
    assert result is True
    assert len(calls) == 1
    call = calls[0]
    ct = call["comment_thread"]
    # verify thread contents were built using our fake classes
    assert isinstance(ct, FakeCommentThread)
    assert ct.status == "open"
    assert isinstance(ct.thread_context, FakeCommentThreadContext)
    assert ct.thread_context.file_path == "path/to/file.py"
    # comments list contains one FakeComment with correct content
    assert isinstance(ct.comments, list) and len(ct.comments) == 1
    assert isinstance(ct.comments[0], FakeComment)
    assert ct.comments[0].content == "please change this"
    # verify the create_thread call parameters
    assert call["project"] == "my_project"
    assert call["repository_id"] == "my_repo"
    assert call["pull_request_id"] == 123
    # ensure no errors were logged
    assert logger.errors == []


def test_publish_code_suggestions_handles_create_thread_exception(monkeypatch):
    logger = setup_common(monkeypatch, settings_dict={"default_comment_status": "closed", "org": "o", "pat": "p"})

    class ExplodingClient:
        def create_thread(self, comment_thread=None, project=None, repository_id=None, pull_request_id=None):
            raise RuntimeError("boom")

    provider = azure_mod.AzureDevopsProvider()
    provider.azure_devops_client = ExplodingClient()
    provider.workspace_slug = "P"
    provider.repo_slug = "R"
    provider.pr_num = 999

    suggestion = {
        "body": "whoops",
        "relevant_file": "afile.py",
        "relevant_lines_start": 1,
        "relevant_lines_end": 1,
    }

    result = provider.publish_code_suggestions([suggestion])
    assert result is True
    # ensure error was logged with suggestion passed in kwargs
    assert len(logger.errors) == 1
    msg, args, kwargs = logger.errors[0]
    assert "Azure failed to publish code suggestion" in msg
    # original suggestion is passed as keyword 'suggestion' per implementation
    assert kwargs.get("suggestion") == suggestion
