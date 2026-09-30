import asyncio
import types
from types import SimpleNamespace
import pytest

import pr_agent.tools.pr_code_suggestions as pcs_module
from pr_agent.tools.pr_code_suggestions import PRCodeSuggestions


class FakeProvider:
    def __init__(self, *, files=True, supported=True, publish_ret=None):
        self._files = files
        self._supported = supported
        self.published = []
        self.removed = []
        self.edited = []
        self.publish_ret = publish_ret or "progress-1"
        self.pr = SimpleNamespace(title="fake-pr-title")

    def get_files(self):
        return self._files

    def get_languages(self):
        # Return a mapping as expected by get_main_pr_language
        return {"python": 1}

    def get_pr_branch(self):
        return "branch"

    def get_commit_messages(self):
        return ["msg1"]

    def get_pr_description(self, split_changes_walkthrough=False):
        # return (description, files)
        return ("desc", ["f1"]) if self._files else ("", [])

    def is_supported(self, fmt):
        return self._supported

    def publish_comment(self, body, is_temporary=False):
        self.published.append((body, is_temporary))
        return self.publish_ret

    def remove_initial_comment(self):
        self.removed.append("initial")

    def remove_comment(self, resp):
        self.removed.append(resp)

    def edit_comment(self, resp, body):
        self.edited.append((resp, body))


class AttrWithGet:
    """Small helper that provides attribute access and a .get method like a dict/object hybrid."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get(self, key, default=None):
        return getattr(self, key, default)


class FakeSettings:
    def __init__(self):
        # pr_code_suggestions should be accessible via attributes and .get()
        self.pr_code_suggestions = AttrWithGet(
            num_code_suggestions_per_chunk=1,
            decouple_hunks=True,
            commitable_code_suggestions=False,
            demand_code_suggestions_self_review=True,
            enable_chat_text=False,
            enable_help_text=True,
            persistent_comment=True,
            max_history_len=3,
            dual_publishing_score_threshold=1,
            extra_instructions="",
        )
        # prompts
        self.pr_code_suggestions_prompt = SimpleNamespace(system="sys", user="user")
        self.pr_code_suggestions_prompt_not_decoupled = SimpleNamespace(system="sys2", user="user2")
        # config used as object with .get and also as dict via get('config')
        self.config = AttrWithGet(publish_output=True,
                                  publish_output_progress=True,
                                  is_auto_command=False,
                                  get=lambda k, d=None: None,
                                  )
        # language extension map used by get_main_pr_language
        self.language_extension_map_org = {"python": [".py"]}
        # small internal dict for get('config', {})
        self._config_dict = {"output_relevant_configurations": True}

    def get(self, key, default=None):
        if key == 'config':
            return self._config_dict
        if key.startswith('config.'):
            _, sub = key.split('.', 1)
            return getattr(self.config, sub, default)
        return default

    def set(self, key, val):
        if key == 'config.enable_ai_metadata':
            setattr(self.config, 'enable_ai_metadata', val)


@pytest.mark.asyncio
async def test_run_returns_none_when_no_files_round_022(monkeypatch):
    """Cover branch where git_provider.get_files() is falsy -> early return None"""
    fake_provider = FakeProvider(files=False)
    monkeypatch.setattr(pcs_module, 'get_git_provider_with_context', lambda pr_url: fake_provider)

    # Patch settings to a minimal fake
    monkeypatch.setattr(pcs_module, 'get_settings', lambda: FakeSettings())

    # Ensure retry_with_fallback_models is not called; if it was, make it fail fast
    async def _boom(*a, **k):
        raise AssertionError("retry_with_fallback_models should not be called when no files")

    monkeypatch.setattr(pcs_module, 'retry_with_fallback_models', _boom)

    pr = PRCodeSuggestions("fake-pr-url")
    # run should simply return None and not raise
    result = await pr.run()
    assert result is None


@pytest.mark.asyncio
async def test_run_calls_publish_no_suggestions_when_no_code_suggestions_round_022(monkeypatch):
    """Cover branch: publish progress comment when supported, fallback to publish_no_suggestions when no suggestions"""
    fake_provider = FakeProvider(files=True, supported=True, publish_ret="progress-xyz")
    monkeypatch.setattr(pcs_module, 'get_git_provider_with_context', lambda pr_url: fake_provider)

    # settings: publish_output True + publish_output_progress True + not auto command
    fake_settings = FakeSettings()
    fake_settings.config.publish_output = True
    fake_settings.config.publish_output_progress = True
    fake_settings.config.is_auto_command = False
    monkeypatch.setattr(pcs_module, 'get_settings', lambda: fake_settings)

    # Patch retry to return None so code sets data = {"code_suggestions": []}
    async def _ret_none(fn, model_type=None):
        return None

    monkeypatch.setattr(pcs_module, 'retry_with_fallback_models', _ret_none)

    # replace publish_no_suggestions to set a flag we can assert
    async def _publish_no_suggestions(self):
        self._no_suggestions_called = True

    monkeypatch.setattr(PRCodeSuggestions, 'publish_no_suggestions', _publish_no_suggestions)

    pr = PRCodeSuggestions("fake-pr-url")
    await pr.run()

    assert getattr(pr, '_no_suggestions_called', False) is True
    # progress_response must have been set from publish_comment
    assert pr.progress_response == "progress-xyz"


@pytest.mark.asyncio
async def test_run_publish_summarized_suggestions_and_persistent_history_round_022(monkeypatch):
    """Cover summarized suggestions publishing path including self-review text, help text, relevant configs, and persistent comment flow"""
    fake_provider = FakeProvider(files=True, supported=True, publish_ret="progress-persist")
    monkeypatch.setattr(pcs_module, 'get_git_provider_with_context', lambda pr_url: fake_provider)

    # Configure settings to trigger summarized suggestions path
    fake_settings = FakeSettings()
    fake_settings.config.publish_output = True
    fake_settings.config.publish_output_progress = True
    fake_settings.config.is_auto_command = False
    # pr_code_suggestions flags
    fake_settings.pr_code_suggestions.commitable_code_suggestions = False
    fake_settings.pr_code_suggestions.demand_code_suggestions_self_review = True
    fake_settings.pr_code_suggestions.enable_help_text = True
    fake_settings.pr_code_suggestions.enable_chat_text = False
    fake_settings.pr_code_suggestions.persistent_comment = True
    fake_settings.pr_code_suggestions.dual_publishing_score_threshold = 1
    monkeypatch.setattr(pcs_module, 'get_settings', lambda: fake_settings)

    # Patch retry to return a data dict with one suggestion
    async def _ret_data(fn, model_type=None):
        return {"code_suggestions": [{"title": "s1", "description": "d"}]}

    monkeypatch.setattr(pcs_module, 'retry_with_fallback_models', _ret_data)

    # Patch generate_summarized_suggestions to return a known body
    monkeypatch.setattr(PRCodeSuggestions, 'generate_summarized_suggestions', lambda self, data: "PR_BODY")

    # Patch add_self_review_text to append some text
    async def _add_self_review_text(self, pr_body):
        return pr_body + "\n--self-review--"

    monkeypatch.setattr(PRCodeSuggestions, 'add_self_review_text', _add_self_review_text)

    # Patch HelpMessage usage guide
    monkeypatch.setattr(pcs_module.HelpMessage, 'get_improve_usage_guide', staticmethod(lambda: "HELP_GUIDE"))

    # Patch show_relevant_configurations
    monkeypatch.setattr(pcs_module, 'show_relevant_configurations', lambda relevant_section=None: "CONFIGS")

    # Patch publish_persistent_comment_with_history to record call
    called = {}

    def _publish_persistent_comment_with_history(self, git_provider, pr_comment, initial_header=None,
                                                 update_header=None, name=None, final_update_message=None,
                                                 max_previous_comments=None, progress_response=None,
                                                 only_fold=None):
        called['persistent'] = dict(
            pr_comment=pr_comment,
            progress_response=progress_response,
            name=name,
        )

    monkeypatch.setattr(PRCodeSuggestions, 'publish_persistent_comment_with_history', _publish_persistent_comment_with_history)

    # Patch dual_publishing to set flag
    async def _dual(self, data):
        called['dual'] = True

    monkeypatch.setattr(PRCodeSuggestions, 'dual_publishing', _dual)

    pr = PRCodeSuggestions("fake-pr-url")
    await pr.run()

    # Assert persistent publishing was invoked with PR_BODY present
    assert 'persistent' in called and called['persistent']['pr_comment'].startswith("PR_BODY")
    # Assert dual publishing awaited
    assert called.get('dual', False) is True
