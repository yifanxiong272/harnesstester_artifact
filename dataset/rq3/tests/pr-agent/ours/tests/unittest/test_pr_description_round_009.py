import asyncio
import types
from types import SimpleNamespace
import pytest

import pr_agent.tools.pr_description as pd

# Small helper mapping that supports both attribute access and dict.get
class AttrDict(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e
    def __setattr__(self, name, value):
        self[name] = value

# Dummy classes and helpers to patch into the module under test
class DummyLogger:
    def info(self, *a, **k):
        pass
    def debug(self, *a, **k):
        pass
    def warning(self, *a, **k):
        pass
    def error(self, *a, **k):
        pass

class DummyAIHandler:
    def __init__(self):
        self.main_pr_language = None

class DummyTokenHandler:
    def __init__(self, pr, vars, system, user):
        self.pr = pr
        self.vars = vars
        self.system = system
        self.user = user

class DummyGitProvider:
    def __init__(self):
        # simple pr object with title
        self.pr = SimpleNamespace(title="Dummy PR Title")
        self._published_comments = []
        self._persistent_comments = []
        self._published_labels = []
        self._description = None
        self._initial_comment_removed = False
        # features toggles are attributes prefixed with supported_
        # default none; tests set them explicitly

    # methods used in __init__ and run
    def get_languages(self):
        return ["python"]
    def get_files(self):
        return ["file1.py"]
    def get_pr_id(self):
        return "PR-123"
    def is_supported(self, feature):
        return getattr(self, "supported_" + feature, False)
    def get_pr_branch(self):
        return "main"
    def get_pr_description(self, full=False):
        return "A short description"
    def get_commit_messages(self):
        return ["commit1", "commit2"]
    def get_diff_files(self):
        return ["file1.py", "file2.py"]
    def publish_comment(self, body, is_temporary=False):
        self._published_comments.append((body, is_temporary))
    def remove_initial_comment(self):
        self._initial_comment_removed = True
    def get_pr_labels(self, update=False):
        return ["existing"]
    def publish_labels(self, labels):
        # store labels tuple for deterministic inspection
        self._published_labels.append(tuple(labels))
    def publish_persistent_comment(self, body, initial_header=None, update_header=None, name=None, final_update_message=None):
        self._persistent_comments.append((body, initial_header, update_header, name, final_update_message))
    def publish_description(self, title, body):
        self._description = (title, body)
    def get_latest_commit_url(self):
        return getattr(self, "latest_commit_url", None)
    def get_pr_url(self):
        return "http://example/pr/123"
    def get_user_description(self):
        return "user provided description"

# Helper settings object that mirrors the shape used by the module under test
class DummySettings:
    def __init__(self, config_overrides=None, pr_description_overrides=None, prompt_system="sys", prompt_user="usr"):
        # top-level config attribute that supports attribute access and get
        cfg = AttrDict({
            "publish_output": False,
            "is_auto_command": False,
            "enable_custom_labels": False,
            # allow .get usage for optional flags
            "duplicate_prompt_examples": False,
        })
        if config_overrides:
            cfg.update(config_overrides)
        self.config = cfg

        # pr_description attributes
        prd = AttrDict({
            "enable_semantic_files_types": False,
            "publish_labels": False,
            "use_description_markers": False,
            "inline_file_summary": True,
            "enable_help_text": False,
            "enable_help_comment": False,
            "publish_description_as_comment": False,
            "publish_description_as_comment_persistent": False,
            "final_update_message": False,
            "extra_instructions": "",
            "collapsible_file_list_threshold": 8,
        })
        if pr_description_overrides:
            prd.update(pr_description_overrides)
        self.pr_description = prd

        # prompt object
        self.pr_description_prompt = SimpleNamespace(system=prompt_system, user=prompt_user)
        # place to be mutated by run() when publish_output is False
        self.data = {}
        # allow .get(key, default) usage at top-level (used by code)
        self._top_map = {"config": cfg}

    def get(self, key, default=None):
        return self._top_map.get(key, default)


@pytest.mark.asyncio
async def test_run_no_prediction_round_009(monkeypatch):
    """Scenario: publish_output True, not auto command, but model returns empty prediction -> initial comment published then removed and function returns None"""
    # Prepare module-level patches
    git = DummyGitProvider()
    git.supported_gfm_markdown = False

    def gp_with_ctx(pr_url):
        return git

    settings = DummySettings(config_overrides={"publish_output": True, "is_auto_command": False})

    # patch functions and classes in module where PRDescription resolves them
    monkeypatch.setattr(pd, "get_git_provider_with_context", gp_with_ctx)
    monkeypatch.setattr(pd, "get_main_pr_language", lambda langs, files: "python")
    monkeypatch.setattr(pd, "get_settings", lambda: settings)
    monkeypatch.setattr(pd, "get_logger", lambda: DummyLogger())
    # ensure ai handler and token handler are deterministic
    monkeypatch.setattr(pd, "LiteLLMAIHandler", DummyAIHandler)
    monkeypatch.setattr(pd, "TokenHandler", DummyTokenHandler)

    # extract_and_cache_pr_tickets no-op async
    async def _noop_extract(*args, **kwargs):
        return None
    monkeypatch.setattr(pd, "extract_and_cache_pr_tickets", _noop_extract)

    # Ensure retry_with_fallback_models will call provided coroutine which we patch to set no prediction
    async def fake_retry(func, model):
        try:
            await func(model)
        except TypeError:
            await func()
    monkeypatch.setattr(pd, "retry_with_fallback_models", fake_retry)

    # Patch PRDescription._prepare_prediction to set an empty prediction
    async def _prepare_prediction_empty(self, model=None):
        self.prediction = None
    monkeypatch.setattr(pd.PRDescription, "_prepare_prediction", _prepare_prediction_empty)

    # instantiate and run, pass DummyAIHandler explicitly to ensure deterministic constructor usage
    pr = pd.PRDescription("http://example/pr/123", ai_handler=DummyAIHandler)
    result = await pr.run()

    # Assertions: initial temporary comment should be published, removed and function returns None
    assert any("Preparing PR description" in (body or "") for (body, is_temp) in git._published_comments)
    assert git._initial_comment_removed is True
    assert result is None


@pytest.mark.asyncio
async def test_run_publish_all_round_009(monkeypatch):
    """Scenario: full-publish flow with labels, persistent comment and final update message paths exercised deterministically."""
    git = DummyGitProvider()
    # enable a few supported features
    git.supported_gfm_markdown = True
    git.supported_get_labels = True
    git.supported_publish_file_comments = False

    def gp_with_ctx(pr_url):
        return git

    # Configure settings to enable many branches
    settings = DummySettings(
        config_overrides={"publish_output": True, "is_auto_command": False, "enable_custom_labels": False},
        pr_description_overrides={
            "enable_semantic_files_types": True,
            "publish_labels": True,
            "use_description_markers": False,
            "inline_file_summary": False,
            "enable_help_text": True,
            "enable_help_comment": False,
            "publish_description_as_comment": True,
            "publish_description_as_comment_persistent": True,
            "final_update_message": True,
        },
    )

    monkeypatch.setattr(pd, "get_git_provider_with_context", gp_with_ctx)
    monkeypatch.setattr(pd, "get_main_pr_language", lambda langs, files: "python")
    monkeypatch.setattr(pd, "get_settings", lambda: settings)
    monkeypatch.setattr(pd, "get_logger", lambda: DummyLogger())
    monkeypatch.setattr(pd, "LiteLLMAIHandler", DummyAIHandler)
    monkeypatch.setattr(pd, "TokenHandler", DummyTokenHandler)

    async def _noop_extract(*args, **kwargs):
        return None
    monkeypatch.setattr(pd, "extract_and_cache_pr_tickets", _noop_extract)

    # Make retry_with_fallback_models a no-op (we'll set prediction manually)
    async def fake_retry_noop(func, model):
        return None
    monkeypatch.setattr(pd, "retry_with_fallback_models", fake_retry_noop)

    # Patch internal preparers to return deterministic values
    monkeypatch.setattr(pd.PRDescription, "_prepare_data", lambda self: setattr(self, "patches_diff", "diff"))
    monkeypatch.setattr(pd.PRDescription, "_prepare_file_labels", lambda self: {"file1.py": ["file-label"]})
    monkeypatch.setattr(pd.PRDescription, "_prepare_labels", lambda self: ["describe-label"]) 
    monkeypatch.setattr(pd.PRDescription, "_prepare_pr_answer", lambda self: ("TitleX", "BodyX", "ChangesWalkthroughX", []))

    # Patch help message and relevant configurations utilities
    monkeypatch.setattr(pd.HelpMessage, "get_describe_usage_guide", staticmethod(lambda: "HELP_GUIDE"))
    monkeypatch.setattr(pd, "show_relevant_configurations", lambda relevant_section=None: "RELEVANT_CONFIGS")

    # Patch get_user_labels to return an extra user label
    monkeypatch.setattr(pd, "get_user_labels", lambda original: ["user"])

    # Set latest commit url to ensure final update message branch
    git.latest_commit_url = "http://commit/sha"

    # instantiate PRDescription and set prediction True to go down the happy path
    pr = pd.PRDescription("http://example/pr/456", ai_handler=DummyAIHandler)
    pr.prediction = True

    # Run
    result = await pr.run()

    # Assertions: published labels, persistent comment, and final update comment should have been invoked
    assert len(git._published_labels) > 0
    assert len(git._persistent_comments) == 1
    assert any(("latest commit" in (body or "") or "updated to latest commit" in (body or "")) for (body, is_temp) in git._published_comments)
    assert git._initial_comment_removed is True
    assert result == ""
