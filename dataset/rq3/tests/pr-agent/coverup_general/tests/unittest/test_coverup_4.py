# file: pr_agent/tools/pr_description.py:203-322
# asked: {"lines": [204, 205, 206, 208, 209, 210, 211, 213, 214, 216, 217, 218, 220, 221, 224, 225, 227, 228, 229, 232, 233, 234, 235, 236, 237, 239, 240, 241, 244, 245, 246, 247, 248, 249, 250, 251, 253, 254, 255, 256, 257, 258, 259, 260, 262, 263, 264, 265, 266, 267, 268, 270, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 303, 304, 305, 308, 309, 310, 311, 314, 317, 318, 319, 320, 321, 322], "branches": [[204, 205], [204, 208], [210, 211], [210, 213], [216, 217], [216, 232], [218, 220], [218, 227], [224, 0], [224, 225], [244, 245], [244, 253], [246, 247], [246, 263], [254, 255], [254, 262], [255, 254], [255, 256], [264, 265], [264, 273], [266, 267], [266, 270], [281, 282], [281, 289], [283, 284], [283, 289], [285, 283], [285, 286], [289, 290], [289, 297], [291, 292], [291, 297], [293, 291], [293, 294], [301, 303], [301, 308], [318, 0], [318, 319], [320, 0], [320, 321]]}
# gained: {"lines": [204, 205, 206, 208, 209, 210, 213, 214, 216, 217, 218, 220, 221, 224, 225, 232, 233, 234, 235, 236, 237, 239, 240, 241, 244, 253, 254, 255, 256, 257, 258, 259, 260, 262, 263, 264, 265, 266, 270, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 289, 290, 291, 292, 293, 297, 298, 299, 300, 301, 303, 304, 305, 308, 309, 310, 311, 314, 317, 318, 319, 320, 321, 322], "branches": [[204, 205], [204, 208], [210, 213], [216, 217], [216, 232], [218, 220], [224, 225], [244, 253], [254, 255], [254, 262], [255, 254], [255, 256], [264, 265], [264, 273], [266, 270], [281, 282], [283, 284], [283, 289], [285, 283], [289, 290], [291, 292], [291, 297], [293, 291], [301, 303], [318, 319], [320, 321]]}

import asyncio
import types
import pytest

import pr_agent.tools.pr_description as pr_desc_mod


class DummyEncoder:
    def encode(self, s):
        return list(range(len(s) if s is not None else 0))


class DummyTokenHandler:
    def __init__(self, *args, **kwargs):
        self.prompt_tokens = 1
        self.encoder = DummyEncoder()


class FakePR:
    def __init__(self):
        self.title = "Fake PR Title"


class FakeGitProvider:
    def __init__(self, user_description=""):
        self.pr = FakePR()
        self._user_description = user_description

    def get_languages(self):
        return ["python"]

    def get_files(self):
        return ["file1.py"]

    def get_pr_id(self):
        return 123

    def is_supported(self, feature):
        return True

    def get_pr_branch(self):
        return "main"

    def get_pr_description(self, full=False):
        return "short description"

    def get_commit_messages(self):
        return ["commit1"]

    def get_diff_files(self):
        return ["file1.py", "file2.py"]

    def get_user_description(self):
        return self._user_description


class FakeSettings:
    def __init__(self, pr_description_kwargs=None, include_contain_keys=None):
        # defaults for pr_description attributes used by PRDescription
        defaults = {
            "use_description_markers": False,
            "enable_semantic_files_types": False,
            "enable_large_pr_handling": False,
            "async_ai_calls": False,
            "extra_instructions": "",
            # collapsible_file_list_threshold accessible via .get
            "collapsible_file_list_threshold": 8,
            "enable_pr_diagram": False,
        }
        if pr_description_kwargs:
            defaults.update(pr_description_kwargs)
        # create a SimpleNamespace for pr_description and add a .get method similar to dict.get
        self.pr_description = types.SimpleNamespace(**defaults)
        def pr_get(name, default=None):
            return getattr(self.pr_description, name, default)
        self.pr_description.get = pr_get

        # prompt namespaces expected at top-level of settings
        self.pr_description_prompt = types.SimpleNamespace(system="sys", user="user")
        self.pr_description_only_files_prompts = types.SimpleNamespace(system="sysf", user="userf")
        self.pr_description_only_description_prompts = types.SimpleNamespace(system="sysd", user="userd")

        # config namespace with get method used in PRDescription
        def config_get(name, default=None):
            # default to False for duplicate_prompt_examples if not set
            return False
        self.config = types.SimpleNamespace(enable_custom_labels=False, get=config_get)

        # support "in" checks on the settings object
        self._contain_keys = set(include_contain_keys or ())

    def __contains__(self, item):
        return item in self._contain_keys


@pytest.mark.asyncio
async def test_prepare_prediction_markers_skip(monkeypatch):
    fake_settings = FakeSettings(
        pr_description_kwargs={
            "use_description_markers": True,
            "enable_semantic_files_types": False,
            "enable_large_pr_handling": False,
            "async_ai_calls": False,
            "extra_instructions": "none"
        }
    )

    monkeypatch.setattr(pr_desc_mod, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(pr_desc_mod, "get_git_provider_with_context", lambda url: FakeGitProvider(user_description="no markers here"))
    monkeypatch.setattr(pr_desc_mod, "get_main_pr_language", lambda langs, files: "python")
    monkeypatch.setattr(pr_desc_mod, "TokenHandler", DummyTokenHandler)

    pr = pr_desc_mod.PRDescription("http://fake/pr")
    assert pr.prediction is None

    result = await pr._prepare_prediction("gpt-test-model")
    assert result is None
    assert pr.prediction is None


@pytest.mark.asyncio
async def test_prepare_prediction_small_pr_sync(monkeypatch):
    fake_settings = FakeSettings(
        pr_description_kwargs={
            "use_description_markers": False,
            "enable_semantic_files_types": True,
            "enable_large_pr_handling": False,
            "async_ai_calls": False,
            "extra_instructions": ""
        }
    )

    monkeypatch.setattr(pr_desc_mod, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(pr_desc_mod, "get_git_provider_with_context", lambda url: FakeGitProvider(user_description=""))
    monkeypatch.setattr(pr_desc_mod, "get_main_pr_language", lambda langs, files: "python")
    monkeypatch.setattr(pr_desc_mod, "TokenHandler", DummyTokenHandler)

    monkeypatch.setattr(pr_desc_mod, "get_pr_diff", lambda *args, **kwargs: ["patch line 1", "patch line 2"])

    pr = pr_desc_mod.PRDescription("http://fake/pr")

    async def fake_get_prediction(model, patches_diff, prompt="pr_description_prompt"):
        return "PREDICTION_HEADER"

    async def fake_extend_uncovered_files(original_prediction):
        return original_prediction + "\nEXTENDED"

    monkeypatch.setattr(pr, "_get_prediction", fake_get_prediction)
    monkeypatch.setattr(pr, "extend_uncovered_files", fake_extend_uncovered_files)

    await pr._prepare_prediction("gpt-test-model")
    assert pr.prediction == "PREDICTION_HEADER\nEXTENDED"


@pytest.mark.asyncio
async def test_prepare_prediction_large_pr_async_clipping_and_yaml_fallback(monkeypatch):
    fake_settings = FakeSettings(
        pr_description_kwargs={
            "use_description_markers": False,
            "enable_semantic_files_types": True,
            "enable_large_pr_handling": True,
            "async_ai_calls": True,
            "extra_instructions": ""
        },
        include_contain_keys={"pr_description_only_files_prompts"}
    )

    monkeypatch.setattr(pr_desc_mod, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(pr_desc_mod, "get_git_provider_with_context", lambda url: FakeGitProvider(user_description=""))
    monkeypatch.setattr(pr_desc_mod, "get_main_pr_language", lambda langs, files: "python")
    monkeypatch.setattr(pr_desc_mod, "TokenHandler", DummyTokenHandler)

    monkeypatch.setattr(pr_desc_mod, "get_pr_diff", lambda *args, **kwargs: [])

    patches_compressed_list = [
        ["pr_files: \n- file1: info"],
        [],
    ]
    total_tokens_list = [10, 5]
    deleted_files_list = ["deleted1.py"]
    remaining_files_list = ["extra1.py", "extra2.py"]
    file_dict = {}
    files_in_patches_list = []

    monkeypatch.setattr(
        pr_desc_mod,
        "get_pr_diff_multiple_patchs",
        lambda *args, **kwargs: (patches_compressed_list, total_tokens_list, deleted_files_list, remaining_files_list, file_dict, files_in_patches_list)
    )

    monkeypatch.setattr(pr_desc_mod, "get_max_tokens", lambda model: 5)

    def fake_clip_tokens(s, max_tokens, num_input_tokens=None):
        return "CLIPPED_CONTENT"
    monkeypatch.setattr(pr_desc_mod, "clip_tokens", fake_clip_tokens)

    def fake_load_yaml(text, keys_fix_yaml=None):
        if text is None:
            return False
        if isinstance(text, str) and "pr_files" in text:
            return False
        return True
    monkeypatch.setattr(pr_desc_mod, "load_yaml", fake_load_yaml)

    pr = pr_desc_mod.PRDescription("http://fake/pr")

    async def fake_get_prediction_instance(model, patches_diff, prompt="pr_description_prompt"):
        if prompt == "pr_description_only_files_prompts":
            return "pr_files:\n- file1: desc"
        elif prompt == "pr_description_only_description_prompts":
            return "HEADERS_ONLY"
        else:
            return "UNKNOWN"

    async def fake_extend_uncovered_files(orig):
        return "EXTENDED_FILES"

    monkeypatch.setattr(pr, "_get_prediction", fake_get_prediction_instance)
    monkeypatch.setattr(pr, "extend_uncovered_files", fake_extend_uncovered_files)

    await pr._prepare_prediction("gpt-test-model")

    assert pr.prediction == "HEADERS_ONLY"
