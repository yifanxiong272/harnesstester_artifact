import pytest
from types import SimpleNamespace
import pr_agent.tools.pr_help_docs as pr_help_docs

# Dummy helpers used to monkeypatch external dependencies in the module
class DummyTokenHandler:
    def __init__(self, a, b, system, user):
        # capture inputs for assertions
        self.init_args = (a, b, system, user)

class DummyAIHandler:
    def __init__(self):
        # mark creation to assert ai_handler was instantiated
        self.ready = True

class DummyGitProvider:
    def __init__(self, url_to_return):
        self._url = url_to_return

    def get_git_repo_url(self, ctx_url):
        # deterministic return
        return self._url

class DummySettings(dict):
    def __init__(self, mapping, prompts_system="sys", prompts_user="user"):
        super().__init__(mapping)
        # provide attribute access expected by the code
        self.pr_help_docs_prompts = SimpleNamespace(system=prompts_system, user=prompts_user)


def _patch_get_logger(monkeypatch):
    # logger used only for debug/exception calls; no-op implementation
    class _Logger:
        def debug(self, *a, **k):
            pass

        def exception(self, *a, **k):
            pass

    monkeypatch.setattr(pr_help_docs, "get_logger", lambda: _Logger())


def test_init_with_missing_settings_round_055(monkeypatch):
    """
    If one of include_root_readme / supported_doc_exts / docs_path is None,
    the constructor should hit the "invalid settings" branch and, because
    the exception is caught, set self.question to None.
    """
    # settings has SUPPORTED_DOC_EXTS explicitly set to None to trigger the branch
    settings = DummySettings({
        "PR_HELP_DOCS.REPO_URL": "http://repo.example",
        "PR_HELP_DOCS.REPO_DEFAULT_BRANCH": "main",
        "PR_HELP_DOCS.EXCLUDE_ROOT_README": False,
        "PR_HELP_DOCS.SUPPORTED_DOC_EXTS": None,
        "PR_HELP_DOCS.DOCS_PATH": "docs/",
    })

    monkeypatch.setattr(pr_help_docs, "get_settings", lambda: settings)
    # safe replacements for other external interactions
    monkeypatch.setattr(pr_help_docs, "get_git_provider_with_context", lambda ctx: object())
    monkeypatch.setattr(pr_help_docs, "TokenHandler", DummyTokenHandler)
    _patch_get_logger(monkeypatch)

    obj = pr_help_docs.PRHelpDocs("ctx://x", ai_handler=DummyAIHandler, args=("Q?",))

    # constructor should have caught the internal exception and set question to None
    assert obj.question is None


def test_init_with_no_git_provider_round_055(monkeypatch):
    """
    When get_git_provider_with_context returns a falsy value, constructor raises
    an exception inside but catches it and sets question to None.
    """
    settings = DummySettings({
        "PR_HELP_DOCS.REPO_URL": "http://repo.example",
        "PR_HELP_DOCS.REPO_DEFAULT_BRANCH": "main",
        "PR_HELP_DOCS.EXCLUDE_ROOT_README": False,
        "PR_HELP_DOCS.SUPPORTED_DOC_EXTS": [".md"],
        "PR_HELP_DOCS.DOCS_PATH": "docs/",
    })

    monkeypatch.setattr(pr_help_docs, "get_settings", lambda: settings)
    # simulate no git provider found
    monkeypatch.setattr(pr_help_docs, "get_git_provider_with_context", lambda ctx: None)
    monkeypatch.setattr(pr_help_docs, "TokenHandler", DummyTokenHandler)
    _patch_get_logger(monkeypatch)

    obj = pr_help_docs.PRHelpDocs("ctx://no-provider", ai_handler=DummyAIHandler, args=("Q?",))
    assert obj.question is None


def test_init_with_unable_to_deduce_repo_round_055(monkeypatch):
    """
    If repo url is empty in settings and the git provider cannot deduce a repo url
    (returns falsy), the constructor should hit the "unable to deduce repo url"
    branch; exception is caught and question should be None.
    """
    settings = DummySettings({
        "PR_HELP_DOCS.REPO_URL": "",  # explicit empty to force deduce branch
        "PR_HELP_DOCS.REPO_DEFAULT_BRANCH": "main",
        "PR_HELP_DOCS.EXCLUDE_ROOT_README": False,
        "PR_HELP_DOCS.SUPPORTED_DOC_EXTS": [".md"],
        "PR_HELP_DOCS.DOCS_PATH": "docs/",
    })

    monkeypatch.setattr(pr_help_docs, "get_settings", lambda: settings)
    # git provider that returns empty -> triggers exception path inside init
    monkeypatch.setattr(pr_help_docs, "get_git_provider_with_context", lambda ctx: DummyGitProvider(""))
    monkeypatch.setattr(pr_help_docs, "TokenHandler", DummyTokenHandler)
    _patch_get_logger(monkeypatch)

    obj = pr_help_docs.PRHelpDocs("ctx://deduce-fails", ai_handler=DummyAIHandler, args=("Q?",))
    assert obj.question is None


def test_init_success_deduce_repo_round_055(monkeypatch):
    """
    Full successful path where settings do not provide an explicit repo url (empty)
    and a git provider deduces a non-empty repo url. Ensure fields are set as expected
    and TokenHandler and AI handler are constructed with deterministic inputs.
    """
    deduced_url = "https://example.com/repo.git"
    settings = DummySettings({
        "PR_HELP_DOCS.REPO_URL": "",  # force deduce branch
        "PR_HELP_DOCS.REPO_DEFAULT_BRANCH": "main",
        "PR_HELP_DOCS.EXCLUDE_ROOT_README": False,
        "PR_HELP_DOCS.SUPPORTED_DOC_EXTS": [".md"],
        "PR_HELP_DOCS.DOCS_PATH": "docs/",
    }, prompts_system="SYS_PROMPT", prompts_user="USER_PROMPT")

    monkeypatch.setattr(pr_help_docs, "get_settings", lambda: settings)
    monkeypatch.setattr(pr_help_docs, "get_git_provider_with_context", lambda ctx: DummyGitProvider(deduced_url))

    # replace TokenHandler to capture the constructor args for verification
    monkeypatch.setattr(pr_help_docs, "TokenHandler", DummyTokenHandler)
    _patch_get_logger(monkeypatch)

    obj = pr_help_docs.PRHelpDocs("ctx://deduce-ok", ai_handler=DummyAIHandler, args=("WHAT?",), return_as_string=True)

    # After successful init the question should be set from args
    assert obj.question == "WHAT?"
    # repo_url was deduced and repo_url_given_explicitly set to False
    assert obj.repo_url == deduced_url
    assert obj.repo_url_given_explicitly is False
    # repo_desired_branch should be None as per the deduce branch
    assert obj.repo_desired_branch is None
    # ensure ai handler instance was created
    assert isinstance(obj.ai_handler, DummyAIHandler)
    # ensure TokenHandler was constructed and captured prompts as provided by settings
    assert hasattr(obj, "token_handler")
    assert isinstance(obj.token_handler, DummyTokenHandler)
    # check that TokenHandler got the system and user prompts from our DummySettings
    a, b, system_prompt, user_prompt = obj.token_handler.init_args
    assert system_prompt == "SYS_PROMPT"
    assert user_prompt == "USER_PROMPT"
