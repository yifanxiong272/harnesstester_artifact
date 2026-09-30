# file: pr_agent/tools/pr_help_docs.py:286-327
# asked: {"lines": [287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 298, 299, 300, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 315, 316, 317, 318, 319, 321, 322, 323, 324, 325, 326, 327], "branches": [[299, 300], [299, 302], [303, 304], [303, 305], [305, 306], [305, 315], [310, 311], [310, 312]]}
# gained: {"lines": [287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 298, 299, 300, 302, 303, 305, 306, 307, 308, 309, 310, 311, 325, 326, 327], "branches": [[299, 300], [299, 302], [303, 305], [305, 306], [310, 311]]}

import pytest

from types import SimpleNamespace


def _make_settings(mapping):
    """
    Return an object that mimics the interface used by PRHelpDocs.get_settings():
    - has .get(key, default)
    - supports __getitem__ access
    - has .pr_help_docs_prompts with .system and .user attributes
    """
    class DummyPrompts:
        def __init__(self, system="sys", user="usr"):
            self.system = system
            self.user = user

    class DummySettings:
        def __init__(self, data):
            self._d = dict(data)
            self.pr_help_docs_prompts = DummyPrompts(system=self._d.get("PROMPT_SYS", "sys"),
                                                     user=self._d.get("PROMPT_USER", "usr"))

        def get(self, key, default=None):
            return self._d.get(key, default)

        def __getitem__(self, key):
            return self._d[key]

    return DummySettings(mapping)


def test_init_raises_on_invalid_setting_and_sets_question_none(monkeypatch):
    """
    Test that when one of the retrieved settings is None, PRHelpDocs __init__
    raises inside try and the except block sets question to None.
    """
    import pr_agent.tools.pr_help_docs as phm

    # Prepare settings where SUPPORTED_DOC_EXTS is None to trigger the Exception at retrieved_settings check
    dummy_settings = _make_settings({
        'PR_HELP_DOCS.REPO_URL': '',
        'PR_HELP_DOCS.REPO_DEFAULT_BRANCH': 'main',
        'PR_HELP_DOCS.EXCLUDE_ROOT_README': False,
        'PR_HELP_DOCS.SUPPORTED_DOC_EXTS': None,  # <-- will cause the "invalid" check to trigger
        'PR_HELP_DOCS.DOCS_PATH': 'docs',
    })

    # Monkeypatch get_settings and get_logger so no real logging or config is used
    monkeypatch.setattr(phm, "get_settings", lambda: dummy_settings)

    # get_git_provider_with_context is not expected to be called before the exception is raised,
    # but patch it defensively to avoid accidental side-effects.
    monkeypatch.setattr(phm, "get_git_provider_with_context", lambda ctx: SimpleNamespace())

    # Provide a get_logger returning an object with exception() method to satisfy the except block
    class DummyLogger:
        def exception(self, *args, **kwargs):
            pass

    monkeypatch.setattr(phm, "get_logger", lambda: DummyLogger())

    # Now construct PRHelpDocs; due to the None setting, it should hit the exception branch and set question to None
    PRHelpDocs = phm.PRHelpDocs
    inst = PRHelpDocs("some_ctx_url", args=("original-question",))

    assert inst.question is None, "question should be set to None by the except handler"
    # Make sure some attributes were attempted to be created (partial validation)
    assert hasattr(inst, "ctx_url")
    assert inst.ctx_url == "some_ctx_url"


def test_init_repo_deduction_fails_and_sets_question_none_and_repo_flag(monkeypatch):
    """
    Test the branch where repo_url is empty, git provider is found, but
    provider.get_git_repo_url returns None causing an exception and exercising
    the except branch (setting question to None). Also verify repo_url_given_explicitly flips to False.
    """
    import pr_agent.tools.pr_help_docs as phm

    # Valid settings so code advances to git provider deduction
    dummy_settings = _make_settings({
        'PR_HELP_DOCS.REPO_URL': '',  # empty -> will try to deduce from git provider
        'PR_HELP_DOCS.REPO_DEFAULT_BRANCH': 'main',
        'PR_HELP_DOCS.EXCLUDE_ROOT_README': False,
        'PR_HELP_DOCS.SUPPORTED_DOC_EXTS': ['md'],
        'PR_HELP_DOCS.DOCS_PATH': 'docs',
    })

    monkeypatch.setattr(phm, "get_settings", lambda: dummy_settings)

    # Create a git provider whose get_git_repo_url returns None to force an exception
    class DummyProvider:
        def __init__(self):
            self.__class__.__name__ = "DummyProvider"

        def get_git_repo_url(self, ctx_url):
            return None

    monkeypatch.setattr(phm, "get_git_provider_with_context", lambda ctx: DummyProvider())

    # Patch logger to avoid noisy logs
    class DummyLogger:
        def debug(self, *a, **k):
            pass

        def exception(self, *a, **k):
            pass

    monkeypatch.setattr(phm, "get_logger", lambda: DummyLogger())

    PRHelpDocs = phm.PRHelpDocs
    inst = PRHelpDocs("ctx://repo", args=("q2",))

    # The exception during init should set question to None
    assert inst.question is None
    # Before the exception happened, repo_url_given_explicitly should have been flipped to False
    assert hasattr(inst, "repo_url_given_explicitly")
    assert inst.repo_url_given_explicitly is False
    # The ctx_url should have been assigned
    assert inst.ctx_url == "ctx://repo"
