import types
import pytest

from pr_agent.tools.pr_help_docs import PRHelpDocs


class MockPrompts:
    def __init__(self, system, user):
        self.system = system
        self.user = user


class MockSettings:
    def __init__(self, mapping, prompts=None):
        self._map = dict(mapping)
        self.pr_help_docs_prompts = prompts or MockPrompts("sys", "usr")

    def get(self, key, default=None):
        return self._map.get(key, default)

    def __getitem__(self, key):
        # Allow KeyError to propagate like a real mapping
        return self._map[key]


class DummyAIHandler:
    def __init__(self):
        self.did_run = False


class DummyTokenHandler:
    created_args = []

    def __init__(self, *args, **kwargs):
        # record call for assertions
        DummyTokenHandler.created_args.append((args, kwargs))


class DummyLogger:
    msgs = {"debug": [], "exception": []}

    def debug(self, msg):
        DummyLogger.msgs["debug"].append(msg)

    def exception(self, msg):
        DummyLogger.msgs["exception"].append(msg)


class DummyProvider:
    def __init__(self, repo_url_to_return):
        self._url = repo_url_to_return

    def get_git_repo_url(self, ctx_url):
        return self._url


# Tests

def test_invalid_setting_round_055(monkeypatch):
    """
    If any of the retrieved settings is None, __init__ should raise internally
    and the instance should end up with question set to None (caught in except).
    """
    # prepare settings where SUPPORTED_DOC_EXTS is None to trigger the any(...) check
    mapping = {
        "PR_HELP_DOCS.REPO_URL": "",
        "PR_HELP_DOCS.REPO_DEFAULT_BRANCH": "main",
        "PR_HELP_DOCS.EXCLUDE_ROOT_README": False,
        "PR_HELP_DOCS.SUPPORTED_DOC_EXTS": None,
        "PR_HELP_DOCS.DOCS_PATH": "docs",
    }
    prompts = MockPrompts(system="s", user="u")
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.get_settings", lambda: MockSettings(mapping, prompts))

    # Prevent actual TokenHandler usage and logger calls
    DummyTokenHandler.created_args.clear()
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.TokenHandler", DummyTokenHandler)
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.get_logger", lambda: DummyLogger())

    # Also ensure git provider resolution is not exercised
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.get_git_provider_with_context", lambda ctx: DummyProvider("irrelevant"))

    p = PRHelpDocs("ctx-url", ai_handler=DummyAIHandler, args=("q",), return_as_string=False)

    # Because an internal exception should have been caught, question must be None
    assert p.question is None
    # TokenHandler must not have been constructed because init should have aborted early
    assert DummyTokenHandler.created_args == []


def test_no_git_provider_round_055(monkeypatch):
    """
    If get_git_provider_with_context returns falsy (None), __init__ raises internally
    and question becomes None.
    """
    mapping = {
        "PR_HELP_DOCS.REPO_URL": "",
        "PR_HELP_DOCS.REPO_DEFAULT_BRANCH": "main",
        "PR_HELP_DOCS.EXCLUDE_ROOT_README": False,
        "PR_HELP_DOCS.SUPPORTED_DOC_EXTS": [".md"],
        "PR_HELP_DOCS.DOCS_PATH": "docs",
    }
    prompts = MockPrompts(system="sys", user="usr")
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.get_settings", lambda: MockSettings(mapping, prompts))

    # Make git provider resolution return None to trigger the branch
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.get_git_provider_with_context", lambda ctx: None)

    DummyTokenHandler.created_args.clear()
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.TokenHandler", DummyTokenHandler)
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.get_logger", lambda: DummyLogger())

    p = PRHelpDocs("ctx-url", ai_handler=DummyAIHandler, args=("q2",), return_as_string=False)

    assert p.question is None
    # No token handler created when git provider missing
    assert DummyTokenHandler.created_args == []


def test_repo_deduction_failure_round_055(monkeypatch):
    """
    If repo_url is not provided and provider returns empty string for get_git_repo_url,
    the code should hit the exception and set question to None but repo_url_given_explicitly
    should be set to False before the failure.
    """
    mapping = {
        "PR_HELP_DOCS.REPO_URL": "",  # empty triggers deduction path
        "PR_HELP_DOCS.REPO_DEFAULT_BRANCH": "main",
        "PR_HELP_DOCS.EXCLUDE_ROOT_README": False,
        "PR_HELP_DOCS.SUPPORTED_DOC_EXTS": [".md"],
        "PR_HELP_DOCS.DOCS_PATH": "docs",
    }
    prompts = MockPrompts(system="s", user="u")
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.get_settings", lambda: MockSettings(mapping, prompts))

    # Provider returns empty string to simulate inability to deduce repo URL
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.get_git_provider_with_context", lambda ctx: DummyProvider(""))
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.TokenHandler", DummyTokenHandler)
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.get_logger", lambda: DummyLogger())

    p = PRHelpDocs("ctx-url", ai_handler=DummyAIHandler, args=("q3",), return_as_string=False)

    # Initialization should have been aborted and question set to None
    assert p.question is None
    # The code path should have set repo_url_given_explicitly to False before failing
    assert p.repo_url_given_explicitly is False


def test_success_with_deduced_repo_round_055(monkeypatch):
    """
    When repo_url isn't explicitly provided, but provider can deduce it, __init__ should
    complete successfully: ai_handler should be instantiated and TokenHandler should be
    constructed with expected variables including docs_url set to the deduced repo URL.
    """
    mapping = {
        "PR_HELP_DOCS.REPO_URL": "",
        "PR_HELP_DOCS.REPO_DEFAULT_BRANCH": "main",
        "PR_HELP_DOCS.EXCLUDE_ROOT_README": False,
        "PR_HELP_DOCS.SUPPORTED_DOC_EXTS": [".md"],
        "PR_HELP_DOCS.DOCS_PATH": "docs",
    }
    prompts = MockPrompts(system="SYS_PROMPT", user="USER_PROMPT")
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.get_settings", lambda: MockSettings(mapping, prompts))

    deduced_url = "https://example.com/myrepo.git"
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.get_git_provider_with_context", lambda ctx: DummyProvider(deduced_url))

    DummyTokenHandler.created_args.clear()
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.TokenHandler", DummyTokenHandler)
    monkeypatch.setattr("pr_agent.tools.pr_help_docs.get_logger", lambda: DummyLogger())

    # Use DummyAIHandler class to be constructed inside PRHelpDocs
    p = PRHelpDocs("ctx-url", ai_handler=DummyAIHandler, args=("the question",), return_as_string=False)

    # Successful path: question should be preserved
    assert p.question == "the question"
    # repo_url should have been deduced and stored
    assert p.repo_url == deduced_url
    # When deduced, repo_desired_branch is set to None per implementation
    assert p.repo_desired_branch is None

    # TokenHandler should have been created exactly once with expected structure
    assert len(DummyTokenHandler.created_args) == 1
    (args, kwargs) = DummyTokenHandler.created_args[0]
    # First arg is None per code, second is the vars dict
    assert args[0] is None
    vars_passed = args[1]
    # vars should contain docs_url mapped to the deduced repo url
    assert vars_passed["docs_url"] == deduced_url
    assert vars_passed["question"] == "the question"
    # third and fourth positional args map to system and user prompts
    assert args[2] == prompts.system
    assert args[3] == prompts.user
