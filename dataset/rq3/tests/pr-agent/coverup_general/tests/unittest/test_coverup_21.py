# file: pr_agent/tools/pr_line_questions.py:55-101
# asked: {"lines": [56, 62, 63, 64, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 81, 82, 83, 84, 85, 86, 87, 88, 89, 91, 92, 93, 95, 96, 97, 99, 101], "branches": [[62, 63], [62, 66], [73, 74], [73, 81], [82, 83], [82, 88], [83, 82], [83, 84], [88, 89], [88, 101], [92, 93], [92, 95], [96, 97], [96, 99]]}
# gained: {"lines": [56, 62, 63, 64, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 81, 82, 83, 84, 85, 86, 87, 88, 89, 91, 92, 93, 95, 96, 97, 99, 101], "branches": [[62, 63], [62, 66], [73, 74], [73, 81], [82, 83], [82, 88], [83, 84], [88, 89], [92, 93], [92, 95], [96, 97], [96, 99]]}

import asyncio
import types
import pytest

import pr_agent.tools.pr_line_questions as plq_module


class DummyPR:
    def __init__(self, title="T"):
        self.title = title


class DummyFile:
    def __init__(self, filename, patch):
        self.filename = filename
        self.patch = patch


class DummyGitProvider:
    def __init__(self, pr_url=None, files=None):
        self.pr = DummyPR(title="dummy")
        self._branch = "branch"
        self._files = files or []
        self.published = None
        self.replied = None

    def get_pr_branch(self):
        return self._branch

    def get_languages(self):
        return ["python"]

    def get_files(self):
        return self._files

    def get_diff_files(self):
        return self._files

    def publish_comment(self, text):
        self.published = text

    def reply_to_comment_from_comment_id(self, comment_id, text):
        self.replied = (comment_id, text)


class DummyGithubProvider(DummyGitProvider):
    # used only for isinstance checks
    pass


class DummyTokenHandler:
    def __init__(self, pr, vars, system, user):
        # minimal behavior required by PR_LineQuestions.__init__
        self.pr = pr
        self.vars = vars
        self.system = system
        self.user = user


class DummyAiHandler:
    def __init__(self):
        self.main_pr_language = None


@pytest.mark.asyncio
async def test_run_with_ask_diff_and_comment_id(monkeypatch):
    """
    Test the branch where get_settings().get('ask_diff_hunk') is truthy, conversation history disabled,
    and a comment_id is provided so reply_to_comment_from_comment_id is used. Also test sanitization
    of model output that starts with a leading slash.
    """
    # Prepare dummy settings object
    class Settings:
        def __init__(self):
            self.pr_questions = types.SimpleNamespace(use_conversation_history=False)
            self.pr_line_questions_prompt = types.SimpleNamespace(system="sys", user="usr")

        def get(self, key, default=None):
            return {
                "ask_diff_hunk": "SOME_DIFF_HUNK",
                "line_start": "",
                "line_end": "",
                "side": "RIGHT",
                "file_name": "ignored",
                "comment_id": "CID-123",
            }.get(key, default)

    settings = Settings()

    # Monkeypatch get_settings in module
    monkeypatch.setattr(plq_module, "get_settings", lambda: settings)

    # Monkeypatch external functions/classes used in run
    # extract_hunk_lines_from_patch should be called with the ask_diff_hunk
    monkeypatch.setattr(
        plq_module,
        "extract_hunk_lines_from_patch",
        lambda patch, filename, line_start="", line_end="", side="RIGHT": ("PATCH_CONTENT\n/line", "1-2"),
    )

    # retry_with_fallback_models should return a string starting with '/'
    async def fake_retry_with_fallback_models(fn, model_type=None):
        return "/starts_with_slash\n/second"
    monkeypatch.setattr(plq_module, "retry_with_fallback_models", fake_retry_with_fallback_models)

    # Ensure ModelType exists (we don't need its value)
    monkeypatch.setattr(plq_module, "ModelType", types.SimpleNamespace(WEAK="WEAK"))

    # Patch TokenHandler and LiteLLMAIHandler to safe dummies
    monkeypatch.setattr(plq_module, "TokenHandler", DummyTokenHandler)
    monkeypatch.setattr(plq_module, "LiteLLMAIHandler", DummyAiHandler)

    # Patch get_git_provider to return a provider factory that yields DummyGitProvider (not GithubProvider)
    monkeypatch.setattr(plq_module, "get_git_provider", lambda: (lambda pr_url: DummyGitProvider(pr_url)))

    # Ensure get_main_pr_language is safe
    monkeypatch.setattr(plq_module, "get_main_pr_language", lambda langs, files: "python")

    # Create the PR_LineQuestions instance
    plq = plq_module.PR_LineQuestions("http://dummy/pr", args=None)

    # Run and assert behavior
    result = await plq.run()
    assert result == ""
    # Because comment_id was provided in settings.get, reply_to_comment_from_comment_id should be used
    assert plq.git_provider.replied is not None
    comment_id, text = plq.git_provider.replied
    # Should preserve the comment_id and text must be sanitized (leading '/' replaced by ' /' and leading space added)
    assert comment_id == "CID-123"
    assert text.startswith(" /starts_with_slash")
    assert "\n /second" in text


@pytest.mark.asyncio
async def test_run_without_ask_diff_and_publish_comment_and_conversation_history(monkeypatch):
    """
    Test branch where ask_diff_hunk is empty, conversation history enabled and git_provider is an instance
    of GithubProvider, so _load_conversation_history is called. Also test publish_comment (no comment_id).
    """
    # Prepare dummy settings object
    class Settings:
        def __init__(self):
            self.pr_questions = types.SimpleNamespace(use_conversation_history=True)
            self.pr_line_questions_prompt = types.SimpleNamespace(system="sys", user="usr")

        def get(self, key, default=None):
            return {
                "ask_diff_hunk": "",
                "line_start": "10",
                "line_end": "20",
                "side": "LEFT",
                "file_name": "target.py",
                "comment_id": "",
            }.get(key, default)

    settings = Settings()
    monkeypatch.setattr(plq_module, "get_settings", lambda: settings)

    # Provide a diff file that matches file_name
    diff_file = DummyFile("target.py", "PATCH_CONTENT_TWO\n/line_in_patch")
    dummy_git = DummyGithubProvider(files=[diff_file])

    # Monkeypatch get_git_provider to return factory producing DummyGithubProvider and ensure GithubProvider type in module
    monkeypatch.setattr(plq_module, "get_git_provider", lambda: (lambda pr_url: dummy_git))
    monkeypatch.setattr(plq_module, "GithubProvider", DummyGithubProvider)

    # Patch extract_hunk_lines_from_patch to be used for diff_files path
    def extract_hunk(patch, filename, line_start="", line_end="", side="RIGHT"):
        # return a patch that includes an inline slash to test newline sanitization
        return ("lineA\nlineB\n/inline", "10-20")
    monkeypatch.setattr(plq_module, "extract_hunk_lines_from_patch", extract_hunk)

    # retry_with_fallback_models returns a string that does not start with '/', but contains a newline slash
    async def fake_retry(fn, model_type=None):
        return "answer line\n/inline"
    monkeypatch.setattr(plq_module, "retry_with_fallback_models", fake_retry)

    # ModelType and handlers
    monkeypatch.setattr(plq_module, "ModelType", types.SimpleNamespace(WEAK="WEAK"))
    monkeypatch.setattr(plq_module, "TokenHandler", DummyTokenHandler)
    monkeypatch.setattr(plq_module, "LiteLLMAIHandler", DummyAiHandler)
    monkeypatch.setattr(plq_module, "get_main_pr_language", lambda langs, files: "python")

    # Patch PR_LineQuestions._load_conversation_history to return a known value
    monkeypatch.setattr(plq_module.PR_LineQuestions, "_load_conversation_history", lambda self: "HISTORY_TEXT")

    # Create instance and run
    plq = plq_module.PR_LineQuestions("http://dummy/pr", args=None)
    result = await plq.run()
    assert result == ""
    # conversation history should have been set in vars
    assert plq.vars["conversation_history"] == "HISTORY_TEXT"
    # publish_comment should have been used (no comment_id)
    assert plq.git_provider.published is not None
    # sanitized should replace "\n/" -> "\n /"
    assert "\n /inline" in plq.git_provider.published
    # make sure text does not start with "/" (should not, since returned string did not start with "/")
    assert not plq.git_provider.published.startswith("/")
