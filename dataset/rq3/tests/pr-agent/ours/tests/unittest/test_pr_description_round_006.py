import asyncio
import types
import pytest

import pr_agent.tools.pr_description as pd

# Helper stubs used in multiple tests
class SettingsStub:
    def __init__(self, pr_description, extras=None):
        self.pr_description = pr_description
        # allow "in settings" checks used in code
        self._extras = extras or {}

    def __contains__(self, key):
        return key in self._extras


class PRDescriptionLike:
    def __init__(self):
        # attributes accessed by _prepare_prediction
        self.user_description = ""
        self.patches_diff = None
        self.prediction = None
        self.pr_id = 123
        self.git_provider = types.SimpleNamespace(pr="fake_pr")
        self.vars = {}
        self.keys_fix = None

    # placeholders for awaitable helpers used by the function under test
    async def _get_prediction(self, *args, **kwargs):
        raise NotImplementedError

    async def extend_uncovered_files(self, original):
        raise NotImplementedError


class SimpleTokenHandler:
    def __init__(self, *args, prompt_tokens=10, encoder_unit_len=1, **kwargs):
        # prompt_tokens used in token math
        self.prompt_tokens = prompt_tokens
        # encoder.encode should return an iterable; the code takes len(...) of it
        class Encoder:
            def __init__(self, unit_len):
                self.unit_len = unit_len

            def encode(self, text):
                # return a list whose length is proportional to the text length
                # unit_len controls coarseness for deterministic behavior
                return ["x"] * (max(1, len(text) // self.unit_len))

        self.encoder = Encoder(encoder_unit_len)


@pytest.mark.asyncio
async def test_markers_skip_round_006(monkeypatch):
    """
    When markers are enabled but the user description does not contain 'pr_agent:',
    the method should log and return None early (lines ~204-206).
    """
    # Prepare settings: pr_description.use_description_markers True
    class PRDescCfg:
        use_description_markers = True

    monkeypatch.setattr(pd, "get_settings", lambda: SettingsStub(PRDescCfg()))

    # Keep logger no-op but track calls via a simple object
    calls = {}

    class LoggerStub:
        def info(self, *args, **kwargs):
            calls.setdefault("info", 0)
            calls["info"] += 1

    monkeypatch.setattr(pd, "get_logger", lambda: LoggerStub())

    # Create a fake instance where user_description lacks the marker
    inst = PRDescriptionLike()
    inst.user_description = "some plain text without marker"

    # Call the unbound async method directly
    result = await pd.PRDescription._prepare_prediction.__get__(inst, pd.PRDescription)("dummy-model")

    assert result is None
    # ensure logger.info was invoked to indicate the skip path
    assert calls.get("info", 0) >= 1


@pytest.mark.asyncio
async def test_patches_diff_with_semantic_extend_round_006(monkeypatch):
    """
    Simulate get_pr_diff returning a non-empty diff string (not a tuple) and
    enable_semantic_files_types True so extend_uncovered_files is awaited.
    This exercises the branch where patches_diff is used (lines ~208-225)
    and ensures prediction gets extended.
    """
    # settings stub: disable markers, disable large PR handling so the simpler branch is used
    class PRDescCfg:
        use_description_markers = False
        enable_large_pr_handling = False
        enable_semantic_files_types = True

    monkeypatch.setattr(pd, "get_settings", lambda: SettingsStub(PRDescCfg()))

    # get_pr_diff returns a plain string (not tuple)
    monkeypatch.setattr(pd, "get_pr_diff", lambda gp, th, model, large_pr_handling, return_remaining_files: "patch-a\npatch-b")

    # Provide logger (no-op) so debug calls don't fail
    monkeypatch.setattr(pd, "get_logger", lambda: types.SimpleNamespace(debug=lambda *a, **k: None))

    # Create instance and stub _get_prediction and extend_uncovered_files
    inst = PRDescriptionLike()

    async def fake_get_prediction(self_model, patches_diff, prompt=None):
        # Return an initial prediction string; actual extension will replace it
        return "initial-prediction"

    async def fake_extend_uncovered_files(original_prediction):
        return "extended_prediction"

    inst._get_prediction = types.MethodType(lambda self, *a, **k: fake_get_prediction(*a, **k), inst)
    inst.extend_uncovered_files = types.MethodType(lambda self, original: fake_extend_uncovered_files(original), inst)

    # Run the target
    await pd.PRDescription._prepare_prediction.__get__(inst, pd.PRDescription)("model-x")

    # Because extend_uncovered_files returns 'extended_prediction', self.prediction should be set to it
    assert inst.prediction == "extended_prediction"


@pytest.mark.asyncio
async def test_large_pr_handling_uses_headers_round_006(monkeypatch):
    """
    Simulate the large PR handling branch. We craft get_pr_diff_multiple_patchs to
    return multiple compressed patches. Use sync ai calls (async_ai_calls False)
    and craft predictions such that the final combined YAML is invalid but the
    header-only prediction is valid. The code should then fall back to using
    headers only (lines ~318-322).
    """
    # settings stub enabling large PR handling and required extras
    class PRDescCfg:
        use_description_markers = False
        enable_large_pr_handling = True
        enable_semantic_files_types = False
        async_ai_calls = False

    extras = {"pr_description_only_files_prompts": True}

    # Also provide nested prompts objects referenced in code
    class OnlyFilesPrompts:
        system = "sys-files"
        user = "user-files"

    class OnlyDescriptionPrompts:
        system = "sys-desc"
        user = "user-desc"

    settings = SettingsStub(PRDescCfg(), extras=extras)
    # attach required named attributes the code expects
    settings.pr_description_only_files_prompts = OnlyFilesPrompts()
    settings.pr_description_only_description_prompts = OnlyDescriptionPrompts()
    settings.pr_description = PRDescCfg()

    monkeypatch.setattr(pd, "get_settings", lambda: settings)

    # Patch TokenHandler used to compute token lengths
    monkeypatch.setattr(pd, "TokenHandler", lambda *a, **k: SimpleTokenHandler(*a, prompt_tokens=5, encoder_unit_len=10))

    # get_pr_diff_multiple_patchs returns tuple of expected shape
    patches_compressed_list = [["file-a-diff"], ["file-b-diff"]]
    total_tokens_list = [1, 1]
    deleted_files_list = [f"deleted_{i}.py" for i in range(3)]
    remaining_files_list = [f"remaining_{i}.py" for i in range(2)]
    file_dict = {}
    files_in_patches_list = []

    monkeypatch.setattr(pd, "get_pr_diff_multiple_patchs",
                        lambda gp, th, model: (patches_compressed_list, total_tokens_list, deleted_files_list, remaining_files_list, file_dict, files_in_patches_list))

    # Make get_logger a no-op object
    monkeypatch.setattr(pd, "get_logger", lambda: types.SimpleNamespace(debug=lambda *a, **k: None,
                                                                        error=lambda *a, **k: None))

    # Provide get_max_tokens large enough to avoid clipping
    monkeypatch.setattr(pd, "get_max_tokens", lambda model: 1000)
    # clip_tokens shouldn't be invoked because tokens are small, but provide a no-op
    monkeypatch.setattr(pd, "clip_tokens", lambda text, max_toks, num_input_tokens=None: text)

    # Prepare instance and behavior for _get_prediction and extend_uncovered_files
    inst = PRDescriptionLike()

    # For file-level predictions, return a YAML-like string that starts with 'pr_files:' so load_yaml returns True
    async def fake_get_prediction_files(model, patches_diff, prompt=None):
        # produce a string that after stripping looks like 'pr_files: <content>'
        return "pr_files:\n  - file: fake"

    # For header prediction (final call) return a clean header
    async def fake_get_prediction_headers(model, patches_diff=None, prompt=None):
        return "pr_headers:\n  title: example"

    # Route calls by checking prompt kwarg
    async def _get_prediction_stub(self_model, patches_diff=None, prompt=None, *args, **kwargs):
        # If prompt name indicates only files prompts, return file predictions
        if prompt == "pr_description_only_files_prompts":
            return await fake_get_prediction_files(None, patches_diff, prompt)
        elif prompt == "pr_description_only_description_prompts":
            return await fake_get_prediction_headers(None, patches_diff, prompt)
        else:
            # fallback
            return ""

    inst._get_prediction = types.MethodType(lambda self, *a, **k: _get_prediction_stub(self, *a, **k), inst)

    # extend_uncovered_files returns an extension part that will make the combined YAML invalid
    async def fake_extend_uncovered_files_bad(original):
        return "INVALID-EXTENSION-NOT-YAML"

    inst.extend_uncovered_files = types.MethodType(lambda self, original: fake_extend_uncovered_files_bad(original), inst)

    # Monkeypatch load_yaml: return False for the full combined prediction but True for header-only
    def fake_load_yaml(text, keys_fix_yaml=None):
        if text.startswith("pr_headers:"):
            return True
        # anything else, including combined 'pr_headers...pr_files' should be invalid for this test
        return False

    monkeypatch.setattr(pd, "load_yaml", fake_load_yaml)

    # Execute
    await pd.PRDescription._prepare_prediction.__get__(inst, pd.PRDescription)("any-model")

    # Because combined YAML is invalid but headers-only is valid, code should set prediction to headers-only
    assert inst.prediction.strip().startswith("pr_headers:"), "Expected fallback to headers-only prediction"
