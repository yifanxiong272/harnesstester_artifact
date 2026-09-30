# file: pr_agent/tools/pr_description.py:203-322
# asked: {"lines": [204, 205, 206, 208, 209, 210, 211, 213, 214, 216, 217, 218, 220, 221, 224, 225, 227, 228, 229, 232, 233, 234, 235, 236, 237, 239, 240, 241, 244, 245, 246, 247, 248, 249, 250, 251, 253, 254, 255, 256, 257, 258, 259, 260, 262, 263, 264, 265, 266, 267, 268, 270, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 303, 304, 305, 308, 309, 310, 311, 314, 317, 318, 319, 320, 321, 322], "branches": [[204, 205], [204, 208], [210, 211], [210, 213], [216, 217], [216, 232], [218, 220], [218, 227], [224, 0], [224, 225], [244, 245], [244, 253], [246, 247], [246, 263], [254, 255], [254, 262], [255, 254], [255, 256], [264, 265], [264, 273], [266, 267], [266, 270], [281, 282], [281, 289], [283, 284], [283, 289], [285, 283], [285, 286], [289, 290], [289, 297], [291, 292], [291, 297], [293, 291], [293, 294], [301, 303], [301, 308], [318, 0], [318, 319], [320, 0], [320, 321]]}
# gained: {"lines": [204, 205, 206, 208, 209, 210, 213, 214, 216, 232, 233, 234, 235, 236, 237, 239, 240, 241, 244, 253, 254, 255, 256, 257, 258, 259, 260, 262, 263, 264, 265, 266, 267, 268, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 303, 304, 305, 308, 309, 310, 311, 314, 317, 318, 319, 320, 321, 322], "branches": [[204, 205], [204, 208], [210, 213], [216, 232], [244, 253], [254, 255], [254, 262], [255, 256], [264, 265], [264, 273], [266, 267], [281, 282], [283, 284], [285, 283], [285, 286], [289, 290], [291, 292], [293, 291], [293, 294], [301, 303], [318, 319], [320, 321]]}

import asyncio
import types
import importlib
from types import SimpleNamespace
import pytest

mod = importlib.import_module("pr_agent.tools.pr_description")
PRDescription = mod.PRDescription

class FakeSettings:
    def __init__(self, **kwargs):
        # default nested namespaces
        self.pr_description = SimpleNamespace(
            use_description_markers=kwargs.get("use_description_markers", False),
            enable_large_pr_handling=kwargs.get("enable_large_pr_handling", False),
            enable_semantic_files_types=kwargs.get("enable_semantic_files_types", False),
            async_ai_calls=kwargs.get("async_ai_calls", False),
        )
        # these are expected to exist as attributes (so "__contains__" can see them)
        # set additional attributes if provided
        if "pr_description_only_files_prompts" in kwargs:
            self.pr_description_only_files_prompts = kwargs["pr_description_only_files_prompts"]
        if "pr_description_only_description_prompts" in kwargs:
            self.pr_description_only_description_prompts = kwargs["pr_description_only_description_prompts"]

    def __contains__(self, key):
        return hasattr(self, key)


class DummyEncoder:
    def __init__(self, encode_len=0):
        self._len = encode_len

    def encode(self, s):
        # return a list whose length is the token count
        return [0] * self._len


class FakeTokenHandler:
    def __init__(self, pr, vars, system_prompt, user_prompt, encode_len=0, prompt_tokens=0):
        self.pr = pr
        self.vars = vars
        self.system = system_prompt
        self.user = user_prompt
        self.encoder = DummyEncoder(encode_len)
        self.prompt_tokens = prompt_tokens


@pytest.mark.asyncio
async def test_use_description_markers_skips_prediction(monkeypatch):
    """
    When markers are required but user_description does not contain 'pr_agent:',
    the method should return early (None) and not set prediction.
    """
    # configure settings to require markers
    fake_settings = FakeSettings(use_description_markers=True)
    monkeypatch.setattr(mod, "get_settings", lambda: fake_settings)

    inst = object.__new__(PRDescription)
    # set required attributes referenced in the early code path
    inst.user_description = "no markers here"
    inst.git_provider = None
    inst.token_handler = None
    inst.vars = None
    inst.pr_id = "test-pr"
    inst.keys_fix = None

    # call
    res = await inst._prepare_prediction("gpt-test-model")

    assert res is None
    # ensure prediction wasn't set
    assert not hasattr(inst, "prediction")


@pytest.mark.asyncio
async def test_large_pr_handling_async_with_clipping_and_fallback(monkeypatch):
    """
    Test the large PR handling path with async AI calls, token clipping and YAML fallback.
    Ensures the code exercises:
     - get_pr_diff returns empty -> triggers large PR branch
     - get_pr_diff_multiple_patchs -> async tasks path
     - file predictions parsed by load_yaml
     - clipping branch (clip_tokens called)
     - final YAML invalid so fallback to headers-only
    """
    # Build fake settings to enable large PR handling and async AI calls
    pr_files_prompt = SimpleNamespace(system="sys_files", user="user_files")
    pr_desc_prompt = SimpleNamespace(system="sys_desc", user="user_desc")
    fake_settings = FakeSettings(
        use_description_markers=False,
        enable_large_pr_handling=True,
        async_ai_calls=True,
        pr_description_only_files_prompts=pr_files_prompt,
        pr_description_only_description_prompts=pr_desc_prompt,
    )
    monkeypatch.setattr(mod, "get_settings", lambda: fake_settings)

    # Monkeypatch get_pr_diff to return an empty patches_diff (falsy) so we go into large_pr_handling branch
    monkeypatch.setattr(mod, "get_pr_diff", lambda *args, **kwargs: [])  # patches_diff = []

    # Prepare values to return from get_pr_diff_multiple_patchs
    # patches_compressed_list: one patch list that will produce a files prediction
    patches_compressed_list = [["pr_files:\n- file1"]]
    total_tokens_list = [1]
    # create large remaining/deleted lists to trigger "Too many ..." behavior and exercise loop breaks
    deleted_files_list = [f"del_{i}" for i in range(60)]
    remaining_files_list = [f"rem_{i}" for i in range(60)]
    file_dict = {}
    files_in_patches_list = []

    monkeypatch.setattr(
        mod,
        "get_pr_diff_multiple_patchs",
        lambda *args, **kwargs: (patches_compressed_list, total_tokens_list, deleted_files_list, remaining_files_list, file_dict, files_in_patches_list),
    )

    # Prepare TokenHandler replacement to control encoding lengths and prompt tokens
    def fake_token_handler_factory(pr, vars, system, user):
        # For files prompt handler, encoder length not relevant
        return FakeTokenHandler(pr, vars, system, user, encode_len=0, prompt_tokens=0)

    monkeypatch.setattr(mod, "TokenHandler", fake_token_handler_factory)

    # Force token count large so that total_tokens > max_tokens_model - OUTPUT_BUFFER_TOKENS_HARD_THRESHOLD
    # Token handler for description prompt will be created inside function; intercept by monkeypatching TokenHandler again in module scope later if necessary
    # But our factory above uses encode_len parameter; we'll monkeypatch TokenHandler to a factory that produces large encode_len when called the second time.
    # Simpler: monkeypatch get_max_tokens to a small value to ensure clipping regardless of token sizes.
    monkeypatch.setattr(mod, "get_max_tokens", lambda model: 10)

    clip_called = {"called": False}
    def fake_clip_tokens(text, max_tokens, num_input_tokens=None):
        clip_called["called"] = True
        # return something noticeably different
        return "CLIPPED_FILES_WALKTHROUGH"
    monkeypatch.setattr(mod, "clip_tokens", fake_clip_tokens)

    # load_yaml behavior:
    # - return True for strings that start with 'pr_files' (to accept per-patch files predictions)
    # - return True for headers-only tokens containing 'HDR_ONLY_VALID'
    # - return False for combined final predictions that contain both 'HDR_ONLY_VALID' and 'pr_files'
    def fake_load_yaml(s, keys_fix_yaml=None):
        if s is None:
            return False
        if isinstance(s, str):
            if s.strip().startswith("pr_files"):
                return True
            if "HDR_ONLY_VALID" in s and "pr_files" not in s:
                return True
            if "HDR_ONLY_VALID" in s and "pr_files" in s:
                return False
        return False

    monkeypatch.setattr(mod, "load_yaml", fake_load_yaml)

    # Provide async _get_prediction behavior on the class: returns per-patch or header strings depending on prompt
    async def fake_get_prediction(self, model, patches_diff=None, prompt=None):
        # Distinguish by prompt argument
        if prompt == "pr_description_only_files_prompts":
            # simulate a per-patch file prediction starting with pr_files
            return "pr_files:\n- file1: description"
        if prompt == "pr_description_only_description_prompts":
            # header prediction that will be considered valid by fake_load_yaml
            return "HDR_ONLY_VALID: yes"
        # default fallback for other prompts
        return ""
    monkeypatch.setattr(PRDescription, "_get_prediction", fake_get_prediction)

    # extend_uncovered_files should just return the files_walkthrough content transformed; used for final assembly
    async def fake_extend_uncovered_files(self, files_walkthrough):
        # return something that will cause the final combined YAML to be invalid per fake_load_yaml logic
        return "- file1: description"
    monkeypatch.setattr(PRDescription, "extend_uncovered_files", fake_extend_uncovered_files)

    # Now create instance of PRDescription bypassing __init__
    inst = object.__new__(PRDescription)
    inst.user_description = ""  # markers not required
    inst.git_provider = SimpleNamespace(pr="fake_pr")
    inst.token_handler = None
    inst.vars = {}
    inst.pr_id = "pr-42"
    inst.keys_fix = None

    # Execute the method (should go through large_pr_handling async path)
    await inst._prepare_prediction("gpt-test-model")

    # After execution, because fake_load_yaml returns False for the combined prediction and True for headers-only,
    # prediction should have been set to the headers-only string ("HDR_ONLY_VALID: yes")
    assert hasattr(inst, "prediction")
    assert inst.prediction == "HDR_ONLY_VALID: yes"

    # Confirm clip_tokens was called as part of the flow
    assert clip_called["called"] is True
