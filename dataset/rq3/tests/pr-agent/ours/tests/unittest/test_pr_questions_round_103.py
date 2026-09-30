import asyncio
from types import SimpleNamespace
import pytest

import pr_agent.tools.pr_questions as pr_q_mod
from pr_agent.tools.pr_questions import PRQuestions


class AttrDict(dict):
    """Dictionary that allows attribute access for keys."""

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError as e:
            raise AttributeError(item) from e


class FakeGitProvider:
    def __init__(self, supported=False):
        # minimal surface used by PRQuestions.__init__ and run
        self.published = []
        self.removed_initial = False
        self._supported = supported
        # PR-like object with a title used by vars
        self.pr = SimpleNamespace(title="FAKE PR TITLE")

    # factory-style call isn't needed because get_git_provider will return a factory
    # but provider instance must implement these methods accessed in __init__
    def get_languages(self):
        return ["python"]

    def get_files(self):
        return ["file1.py"]

    def get_pr_branch(self):
        return "feature-branch"

    def get_pr_description(self):
        return "A fake PR description"

    def get_commit_messages(self):
        return ["Initial commit"]

    def publish_comment(self, comment, is_temporary=False):
        self.published.append({"comment": comment, "is_temporary": is_temporary})

    def remove_initial_comment(self):
        self.removed_initial = True

    def is_supported(self, name):
        return self._supported


async def _fake_retry_with_fallback(target, model_type=None):
    # deterministically call the provided async target with None
    await target(None)


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.debugs = []

    def info(self, *args, **kwargs):
        self.infos.append((args, kwargs))

    def debug(self, *args, **kwargs):
        self.debugs.append((args, kwargs))


def make_fake_settings(publish_output: bool, enable_help_text: bool):
    pr_questions = AttrDict({"enable_help_text": enable_help_text})
    config = AttrDict({"publish_output": publish_output})
    # supply prompt shapes used by TokenHandler constructor call in __init__
    pr_questions_prompt = SimpleNamespace(system="SYS_PROMPT", user="USER_PROMPT")
    return SimpleNamespace(pr_questions=pr_questions, config=config, pr_questions_prompt=pr_questions_prompt)


class DummyTokenHandler:
    def __init__(self, pr, vars_, system, user):
        # store for inspection if needed; do nothing else
        self.pr = pr
        self.vars = vars_
        self.system = system
        self.user = user


@pytest.mark.asyncio
async def test_run_publish_and_help_round_103(monkeypatch):
    """
    Covers: publish_output True path including initial temporary publish, help text appended when provider supports gfm_markdown, and final publish + remove_initial_comment.
    """

    fake_provider = FakeGitProvider(supported=True)
    fake_logger = DummyLogger()

    # get_git_provider should return a factory that accepts pr_url and returns provider
    monkeypatch.setattr(pr_q_mod, "get_git_provider", lambda: (lambda pr_url: fake_provider))
    monkeypatch.setattr(pr_q_mod, "get_logger", lambda: fake_logger)
    monkeypatch.setattr(pr_q_mod, "retry_with_fallback_models", _fake_retry_with_fallback)
    monkeypatch.setattr(pr_q_mod, "HelpMessage", SimpleNamespace(get_ask_usage_guide=lambda: "HELP_GUIDE"))

    # settings: publish_output True, help enabled True
    monkeypatch.setattr(pr_q_mod, "get_settings", lambda: make_fake_settings(publish_output=True, enable_help_text=True))

    # prevent reliance on TokenHandler and main pr language resolution
    monkeypatch.setattr(pr_q_mod, "TokenHandler", DummyTokenHandler)
    monkeypatch.setattr(pr_q_mod, "get_main_pr_language", lambda langs, files: "python")

    # Construct PRQuestions with ai_handler as a callable that returns a simple object
    pr = PRQuestions("http://fake/pr", args={}, ai_handler=lambda: SimpleNamespace())

    # Patch instance methods used in run
    monkeypatch.setattr(pr, "identify_image_in_comment", lambda: None)

    async def fake_prepare_prediction(model):
        fake_logger.debug("_prepare_prediction called", artifact=model)

    monkeypatch.setattr(pr, "_prepare_prediction", fake_prepare_prediction)
    monkeypatch.setattr(pr, "_prepare_pr_answer", lambda: "BASE_COMMENT")

    result = await pr.run()

    assert result == ""

    # initial temporary publish should have been called
    assert any(p["is_temporary"] for p in fake_provider.published), "expected a temporary preparing comment"

    # final non-temporary publish should include BASE_COMMENT and HELP_GUIDE
    non_temps = [p for p in fake_provider.published if not p["is_temporary"]]
    assert non_temps, "expected a final publish_comment call"
    assert "BASE_COMMENT" in non_temps[-1]["comment"]
    assert "HELP_GUIDE" in non_temps[-1]["comment"]

    assert fake_provider.removed_initial is True


@pytest.mark.asyncio
async def test_run_no_publish_with_image_round_103(monkeypatch):
    """
    Covers: publish_output False path, identify_image_in_comment truthy branch (image debug), no help appended when provider not supported or help disabled, and no publish/remove calls.
    """

    fake_provider = FakeGitProvider(supported=False)
    fake_logger = DummyLogger()

    monkeypatch.setattr(pr_q_mod, "get_git_provider", lambda: (lambda pr_url: fake_provider))
    monkeypatch.setattr(pr_q_mod, "get_logger", lambda: fake_logger)
    monkeypatch.setattr(pr_q_mod, "retry_with_fallback_models", _fake_retry_with_fallback)
    monkeypatch.setattr(pr_q_mod, "HelpMessage", SimpleNamespace(get_ask_usage_guide=lambda: "SHOULD_NOT_APPEAR"))

    # settings: publish_output False, help enabled False
    monkeypatch.setattr(pr_q_mod, "get_settings", lambda: make_fake_settings(publish_output=False, enable_help_text=False))

    monkeypatch.setattr(pr_q_mod, "TokenHandler", DummyTokenHandler)
    monkeypatch.setattr(pr_q_mod, "get_main_pr_language", lambda langs, files: "python")

    pr = PRQuestions("http://fake/pr", args={}, ai_handler=lambda: SimpleNamespace())

    # identify_image_in_comment returns truthy to exercise that branch
    monkeypatch.setattr(pr, "identify_image_in_comment", lambda: "images/foo.png")

    async def fake_prepare_prediction(model):
        fake_logger.debug("_prepare_prediction called with", model)

    monkeypatch.setattr(pr, "_prepare_prediction", fake_prepare_prediction)
    monkeypatch.setattr(pr, "_prepare_pr_answer", lambda: "NO_PUBLISH_COMMENT")

    result = await pr.run()

    assert result == ""

    # Because publish_output False, there should be no published comments at all
    assert fake_provider.published == []

    # remove_initial_comment should not have been called
    assert fake_provider.removed_initial is False

    # Ensure a debug log about image identification occurred (artifact kwarg or message)
    found_image_debug = any(
        (len(args) and "Image path identified" in args[0]) or (kwargs and "artifact" in kwargs and kwargs["artifact"] == "images/foo.png")
        for args, kwargs in fake_logger.debugs
    )

    assert found_image_debug or any("images/foo.png" in str(a) for a, _ in fake_logger.debugs), "expected an image debug entry"
