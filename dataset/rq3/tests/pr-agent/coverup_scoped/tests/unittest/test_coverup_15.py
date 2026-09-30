# file: pr_agent/tools/pr_line_questions.py:55-101
# asked: {"lines": [56, 62, 63, 64, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 81, 82, 83, 84, 85, 86, 87, 88, 89, 91, 92, 93, 95, 96, 97, 99, 101], "branches": [[62, 63], [62, 66], [73, 74], [73, 81], [82, 83], [82, 88], [83, 82], [83, 84], [88, 89], [88, 101], [92, 93], [92, 95], [96, 97], [96, 99]]}
# gained: {"lines": [56, 62, 63, 64, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 81, 82, 83, 84, 85, 86, 87, 88, 89, 91, 92, 93, 95, 96, 97, 99, 101], "branches": [[62, 63], [62, 66], [73, 74], [73, 81], [82, 83], [82, 88], [83, 84], [88, 89], [92, 93], [92, 95], [96, 97], [96, 99]]}

import asyncio
import types
import pytest

import pr_agent.tools.pr_line_questions as pr_lq_module


class DummyPR:
    def __init__(self, title="PR Title"):
        self.title = title


class MockFile:
    def __init__(self, filename, patch):
        self.filename = filename
        self.patch = patch


class MockGitProvider:
    """A mock provider that is NOT the GithubProvider class"""
    def __init__(self, pr_url=None):
        self.pr = DummyPR()
        self._branch = "feature/xyz"
        self._diff_files = []
        self.published = None
        self.replied = None

    def get_pr_branch(self):
        return self._branch

    def get_diff_files(self):
        return self._diff_files

    def get_languages(self):
        return ["python"]

    def get_files(self):
        return []

    def publish_comment(self, text):
        self.published = text

    def reply_to_comment_from_comment_id(self, comment_id, text):
        self.replied = (comment_id, text)


class MockGithubProvider(MockGitProvider):
    """A mock provider that should be considered an instance of GithubProvider"""
    pass


class DummyTokenHandler:
    def __init__(self, pr, vars_, system_prompt, user_prompt):
        # store for introspection if needed
        self.pr = pr
        self.vars = vars_
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt


class Settings:
    def __init__(self, values=None, use_conversation_history=False):
        self.values = values or {}
        # nested object for pr_questions
        self.pr_questions = types.SimpleNamespace(use_conversation_history=use_conversation_history)
        # placeholders used in __init__ by TokenHandler
        self.pr_line_questions_prompt = types.SimpleNamespace(system="sys", user="usr")

    def get(self, key, default=None):
        return self.values.get(key, default)


class DummyAIHandler:
    def __init__(self):
        # will be set by PR_LineQuestions.__init__
        self.main_pr_language = None


@pytest.mark.asyncio
async def test_run_with_ask_diff_and_publish_comment(monkeypatch):
    """
    Test branch where ask_diff is provided (so extract_hunk_lines_from_patch is used)
    and comment_id is empty so publish_comment is called.
    Also tests sanitization when model answer starts with '/' and contains '\n/'.
    """
    # Prepare mock provider and factory
    provider = MockGitProvider()
    monkeypatch.setattr(pr_lq_module, "get_git_provider", lambda: (lambda url: provider))
    # Ensure isinstance check for GithubProvider is False for this test (conversation_history off)
    monkeypatch.setattr(pr_lq_module, "GithubProvider", MockGithubProvider)

    # Monkeypatch TokenHandler to avoid heavy initialization
    monkeypatch.setattr(pr_lq_module, "TokenHandler", DummyTokenHandler)
    # Monkeypatch get_main_pr_language to simple value
    monkeypatch.setattr(pr_lq_module, "get_main_pr_language", lambda langs, files: "python")

    # Stub extract_hunk_lines_from_patch to return content
    def fake_extract(patch, filename, line_start=None, line_end=None, side=None):
        return ("+added_line\n/should_be_spaced\nanother\n/and_here", "1-4")
    monkeypatch.setattr(pr_lq_module, "extract_hunk_lines_from_patch", fake_extract)

    # Stub retry_with_fallback_models to return a model answer starting with "/" and containing "\n/"
    async def fake_retry(func, model_type=None):
        # do not call func, just return crafted answer
        return "/leading_slash\n/inner_slash"
    monkeypatch.setattr(pr_lq_module, "retry_with_fallback_models", fake_retry)

    # Provide settings with ask_diff_hunk set, comment_id empty
    settings = Settings(values={
        "ask_diff_hunk": "some diff",
        "line_start": "1",
        "line_end": "4",
        "side": "RIGHT",
        "file_name": "foo.py",
        "comment_id": ""
    }, use_conversation_history=False)
    monkeypatch.setattr(pr_lq_module, "get_settings", lambda: settings)

    # Create instance with a dummy AI handler class so ai_handler() returns an object
    plq = pr_lq_module.PR_LineQuestions("http://example.com/pr/1", args=None, ai_handler=DummyAIHandler)

    # Ensure initial state
    assert plq.vars["conversation_history"] == ""

    # Run
    res = await plq.run()

    # After run, because ask_diff was set, patch_with_lines should be non-empty
    assert plq.patch_with_lines != ""
    # And provider.publish_comment should have been called with sanitized text
    expected = " /leading_slash\n /inner_slash"
    assert provider.published == expected
    # run always returns "", per implementation
    assert res == ""


@pytest.mark.asyncio
async def test_run_with_diff_files_and_reply_to_comment_and_conversation_history(monkeypatch):
    """
    Test branch where ask_diff is empty, provider.get_diff_files is used, and conversation history
    is loaded when provider is an instance of GithubProvider. Also tests reply_to_comment path.
    """
    # Prepare mock github provider and factory
    provider = MockGithubProvider()
    provider._diff_files = [MockFile("match.py", "patch content")]
    monkeypatch.setattr(pr_lq_module, "get_git_provider", lambda: (lambda url: provider))
    # Ensure isinstance check for GithubProvider passes
    monkeypatch.setattr(pr_lq_module, "GithubProvider", MockGithubProvider)

    # Monkeypatch TokenHandler and main language
    monkeypatch.setattr(pr_lq_module, "TokenHandler", DummyTokenHandler)
    monkeypatch.setattr(pr_lq_module, "get_main_pr_language", lambda langs, files: "python")

    # Stub extract_hunk_lines_from_patch to return content for the file's patch
    def fake_extract_from_file(patch, filename, line_start=None, line_end=None, side=None):
        return ("context\n/line", "2-3")
    monkeypatch.setattr(pr_lq_module, "extract_hunk_lines_from_patch", fake_extract_from_file)

    # Stub retry to return an answer that does NOT start with '/', to test publish reply path without extra leading space
    async def fake_retry(func, model_type=None):
        return "OK answer\n/inside"
    monkeypatch.setattr(pr_lq_module, "retry_with_fallback_models", fake_retry)

    # Prepare settings: no ask_diff_hunk, file_name matches, comment_id present, conversation history enabled
    settings = Settings(values={
        "ask_diff_hunk": "",
        "line_start": "",
        "line_end": "",
        "side": "RIGHT",
        "file_name": "match.py",
        "comment_id": "CMT123"
    }, use_conversation_history=True)
    monkeypatch.setattr(pr_lq_module, "get_settings", lambda: settings)

    # Monkeypatch _load_conversation_history to verify it is called and to return a string
    called = {"cnt": 0}

    def fake_load_history(self):
        called["cnt"] += 1
        return "conversation history content"
    monkeypatch.setattr(pr_lq_module.PR_LineQuestions, "_load_conversation_history", fake_load_history)

    # Create instance with DummyAIHandler
    plq = pr_lq_module.PR_LineQuestions("http://example.com/pr/2", args=None, ai_handler=DummyAIHandler)

    # Run
    res = await plq.run()

    # Verify conversation history was loaded and stored in vars
    assert called["cnt"] == 1
    assert plq.vars["conversation_history"] == "conversation history content"

    # Because comment_id is present, reply_to_comment_from_comment_id should have been called with sanitized result
    expected = "OK answer\n /inside"
    assert provider.replied == ("CMT123", expected)
    assert res == ""
