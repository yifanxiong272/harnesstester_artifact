# file: pr_agent/tools/pr_description.py:95-201
# asked: {"lines": [96, 97, 98, 99, 100, 101, 102, 105, 107, 109, 110, 112, 113, 114, 116, 117, 119, 120, 121, 123, 125, 126, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 146, 153, 154, 156, 159, 160, 161, 162, 163, 164, 165, 166, 167, 169, 172, 173, 174, 175, 176, 177, 178, 179, 181, 183, 186, 187, 188, 189, 190, 191, 192, 194, 195, 196, 197, 198, 199, 201], "branches": [[101, 102], [101, 105], [109, 110], [109, 112], [116, 117], [116, 119], [120, 121], [120, 123], [125, 126], [125, 128], [129, 131], [129, 132], [135, 136], [135, 139], [139, 140], [139, 153], [140, 141], [140, 146], [153, 154], [153, 156], [156, 159], [156, 194], [159, 160], [159, 172], [165, 166], [165, 169], [172, 173], [172, 183], [174, 175], [174, 181], [186, 187], [186, 192], [188, 189], [188, 192]]}
# gained: {"lines": [96, 97, 98, 99, 100, 101, 102, 105, 107, 109, 110, 112, 113, 114, 116, 119, 120, 121, 123, 125, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 153, 156, 159, 160, 161, 162, 163, 164, 165, 166, 167, 172, 173, 174, 175, 176, 177, 178, 179, 192, 194, 195, 196, 201], "branches": [[101, 102], [101, 105], [109, 110], [109, 112], [116, 119], [120, 121], [120, 123], [125, 128], [129, 131], [135, 136], [135, 139], [139, 153], [153, 156], [156, 159], [156, 194], [159, 160], [165, 166], [172, 173], [174, 175]]}

import asyncio
from types import SimpleNamespace

import pytest

import pr_agent.tools.pr_description as pr_desc_mod
from pr_agent.tools.pr_description import PRDescription


class FakeGitProvider:
    def __init__(self, supports=None, pr_id="1", title="T", branch="main", description="", commit_msgs="", diff_files=None,
                 user_description="", pr_labels=None, latest_commit_url=None, pr_url="http://pr"):
        self._supports = supports or {}
        self.pr = SimpleNamespace(title=title)
        self._pr_id = pr_id
        self._branch = branch
        self._description = description
        self._commit_msgs = commit_msgs
        self._diff_files = diff_files if diff_files is not None else []
        self._user_description = user_description
        self._pr_labels = pr_labels if pr_labels is not None else []
        self._latest_commit_url = latest_commit_url
        self._pr_url = pr_url

        # record calls
        self.published_comments = []
        self.persistent_comments = []
        self.published_labels = []
        self.published_descriptions = []
        self.removed_initial = False

    # methods used in PRDescription.__init__
    def get_pr_id(self):
        return self._pr_id

    def get_pr_branch(self):
        return self._branch

    def get_pr_description(self, full=False):
        return self._description

    def get_commit_messages(self):
        return self._commit_msgs

    def get_diff_files(self):
        return self._diff_files

    def get_user_description(self):
        return self._user_description

    def get_languages(self):
        return ["python"]

    def get_files(self):
        return ["file1.py"]

    # methods used in run
    def is_supported(self, feature):
        return self._supports.get(feature, False)

    def publish_comment(self, body, is_temporary=False):
        self.published_comments.append((body, is_temporary))

    def publish_persistent_comment(self, *args, **kwargs):
        self.persistent_comments.append((args, kwargs))

    def publish_labels(self, labels):
        self.published_labels.append(list(labels))

    def get_pr_labels(self, update=False):
        # emulate update param, just return the current stored labels
        return list(self._pr_labels)

    def publish_description(self, title, body):
        self.published_descriptions.append((title, body))

    def remove_initial_comment(self):
        self.removed_initial = True

    def get_latest_commit_url(self):
        return self._latest_commit_url

    def get_pr_url(self):
        return self._pr_url


class DummyConfig(dict):
    def __init__(self, publish_output=False, is_auto_command=False, enable_custom_labels=False, duplicate_prompt_examples=False):
        super().__init__()
        # keep mapping keys for dict(get_settings().config)
        self.update({"is_auto_command": is_auto_command, "duplicate_prompt_examples": duplicate_prompt_examples})
        # attributes accessed directly
        self.publish_output = publish_output
        self.enable_custom_labels = enable_custom_labels


class DummyPrDescription(dict):
    def __init__(self, **kwargs):
        # default values
        defaults = dict(
            enable_semantic_files_types=False,
            publish_labels=False,
            use_description_markers=False,
            enable_help_text=False,
            enable_help_comment=False,
            inline_file_summary=False,
            publish_description_as_comment=False,
            publish_description_as_comment_persistent=False,
            final_update_message=False,
            extra_instructions="",
            enable_pr_diagram=False,
            collapsible_file_list_threshold=8,
            output_relevant_configurations=False,
        )
        defaults.update(kwargs)
        super().__init__(defaults)
        # set attributes for direct access like settings.pr_description.publish_labels
        for k, v in defaults.items():
            setattr(self, k, v)


class DummySettings:
    def __init__(self, pr_description_obj, config_obj, pr_description_prompt):
        self.pr_description = pr_description_obj
        self.config = config_obj
        self.pr_description_prompt = pr_description_prompt
        self.data = {}

    def get(self, key, default=None):
        return getattr(self, key, default)


@pytest.mark.asyncio
async def test_run_with_empty_prediction_calls_remove_and_returns_none(monkeypatch):
    # Setup settings where publish_output True to exercise removal path
    pr_desc = DummyPrDescription(enable_semantic_files_types=False)
    config = DummyConfig(publish_output=True, is_auto_command=False)
    settings = DummySettings(pr_desc, config, SimpleNamespace(system="", user=""))
    monkeypatch.setattr(pr_desc_mod, "get_settings", lambda: settings)

    # Provide fake provider
    fake = FakeGitProvider(supports={"gfm_markdown": False})
    monkeypatch.setattr(pr_desc_mod, "get_git_provider_with_context", lambda url: fake)
    monkeypatch.setattr(pr_desc_mod, "get_main_pr_language", lambda langs, files: "python")

    # stub out external async functions
    async def dummy_extract(provider, vars):
        # ensure called with our fake provider
        assert provider is fake

    async def dummy_retry(cb, model):
        # call the callback which should set prediction to None for this test
        await cb("model-x")

    monkeypatch.setattr(pr_desc_mod, "extract_and_cache_pr_tickets", dummy_extract)
    monkeypatch.setattr(pr_desc_mod, "retry_with_fallback_models", dummy_retry)

    # Create instance and monkeypatch _prepare_prediction to set empty prediction
    inst = PRDescription("http://fake/pr", ai_handler=lambda: SimpleNamespace())

    async def _prepare_prediction(model):
        inst.prediction = None  # empty prediction path

    inst._prepare_prediction = _prepare_prediction

    # Run
    result = await inst.run()

    # Expectations: remove_initial_comment called and result is None
    assert fake.removed_initial is True
    assert result is None


@pytest.mark.asyncio
async def test_run_with_publish_output_false_sets_settings_data_and_returns(monkeypatch):
    # Setup settings where publish_output False to hit lines 194-196
    pr_desc = DummyPrDescription(enable_semantic_files_types=False)
    config = DummyConfig(publish_output=False, is_auto_command=False)
    settings = DummySettings(pr_desc, config, SimpleNamespace(system="", user=""))
    monkeypatch.setattr(pr_desc_mod, "get_settings", lambda: settings)

    # Provide fake provider (gfm does not matter)
    fake = FakeGitProvider(supports={"gfm_markdown": False}, diff_files=["a", "b"])
    monkeypatch.setattr(pr_desc_mod, "get_git_provider_with_context", lambda url: fake)
    monkeypatch.setattr(pr_desc_mod, "get_main_pr_language", lambda langs, files: "python")

    # stub external calls
    async def dummy_extract(provider, vars):
        pass

    async def dummy_retry(cb, model):
        await cb("m")

    monkeypatch.setattr(pr_desc_mod, "extract_and_cache_pr_tickets", dummy_extract)
    monkeypatch.setattr(pr_desc_mod, "retry_with_fallback_models", dummy_retry)

    # Create instance and set prediction and necessary helpers
    inst = PRDescription("http://fake/pr", ai_handler=lambda: SimpleNamespace())

    async def _prepare_prediction(model):
        inst.prediction = "SOME PREDICTION"

    inst._prepare_prediction = _prepare_prediction

    # Make _prepare_data and _prepare_pr_answer minimal
    def _prepare_data():
        pass

    inst._prepare_data = _prepare_data

    def _prepare_pr_answer():
        return ("T", "BODY", "WALK", [])

    inst._prepare_pr_answer = _prepare_pr_answer

    # Run
    result = await inst.run()

    # Should set settings.data artifact and return None
    assert settings.data.get("artifact") is not None
    assert "BODY" in settings.data["artifact"]
    assert result is None


@pytest.mark.asyncio
async def test_run_full_publish_path_publishes_labels_and_persistent_comment_and_final_update(monkeypatch):
    # Setup settings for full publishing
    pr_desc = DummyPrDescription(enable_semantic_files_types=False, publish_labels=True, use_description_markers=False,
                                enable_help_text=True, enable_help_comment=False, inline_file_summary=False,
                                publish_description_as_comment=True, publish_description_as_comment_persistent=True,
                                final_update_message=True)
    config = DummyConfig(publish_output=True, is_auto_command=False, enable_custom_labels=True)
    settings = DummySettings(pr_desc, config, SimpleNamespace(system="", user=""))
    monkeypatch.setattr(pr_desc_mod, "get_settings", lambda: settings)

    # Fake provider supports gfm_markdown
    fake = FakeGitProvider(
        supports={"gfm_markdown": True, "get_labels": True, "publish_file_comments": True},
        pr_labels=["existing_label"],
        latest_commit_url="http://commit",
        pr_url="http://pr-url",
    )
    monkeypatch.setattr(pr_desc_mod, "get_git_provider_with_context", lambda url: fake)
    monkeypatch.setattr(pr_desc_mod, "get_main_pr_language", lambda langs, files: "python")

    # stub out external async functions
    async def dummy_extract(provider, vars):
        assert provider is fake

    async def dummy_retry(cb, model):
        await cb("m")

    monkeypatch.setattr(pr_desc_mod, "extract_and_cache_pr_tickets", dummy_extract)
    monkeypatch.setattr(pr_desc_mod, "retry_with_fallback_models", dummy_retry)

    # HelpMessage content
    monkeypatch.setattr(pr_desc_mod.HelpMessage, "get_describe_usage_guide", staticmethod(lambda: "HELP-USAGE"))

    # get_user_labels should return some user labels so merging occurs
    monkeypatch.setattr(pr_desc_mod, "get_user_labels", lambda orig: ["existing_label_user"])

    # Provide instance and patch internal methods
    inst = PRDescription("http://fake/pr", ai_handler=lambda: SimpleNamespace())

    async def _prepare_prediction(model):
        inst.prediction = "PRED"

    inst._prepare_prediction = _prepare_prediction

    def _prepare_data():
        pass

    inst._prepare_data = _prepare_data

    def _prepare_pr_answer():
        return ("My Title", "My Body", "CHANGES", [])

    inst._prepare_pr_answer = _prepare_pr_answer

    def _prepare_labels():
        return ["new_label"]

    inst._prepare_labels = _prepare_labels

    # Run
    result = await inst.run()

    # Assertions: labels published, persistent comment called, final update comment published, and initial comment removed
    assert fake.published_labels, "expected labels to be published"
    assert set(fake.published_labels[-1]) == set(["new_label", "existing_label_user"])
    assert fake.persistent_comments, "expected persistent comment to be published"
    published_texts = [c[0] for c in fake.published_comments]
    # There may be temporary preparation comments; ensure at least one comment exists or persistent was used
    assert published_texts or fake.persistent_comments
    assert fake.removed_initial is True
    # final run returns empty string per function end
    assert result == ""
