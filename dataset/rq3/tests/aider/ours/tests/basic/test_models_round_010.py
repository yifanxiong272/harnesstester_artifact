import pytest

from aider.models import Model


def _make_bare_model():
    # Construct Model instance without running __init__ to avoid external side effects
    m = Model.__new__(Model)
    # Provide the attributes apply_generic_model_settings expects to read or write
    m.name = None
    m.edit_format = "whole"
    m.use_repo_map = False
    m.send_undo_reply = False
    m.lazy = False
    m.overeager = False
    m.reminder = "user"
    m.examples_as_sys_msg = False
    m.extra_params = None
    m.cache_control = False
    m.caches_by_default = False
    m.use_system_prompt = True
    m.use_temperature = True
    m.streaming = True
    m.editor_model_name = None
    m.editor_edit_format = None
    m.reasoning_tag = None
    m.remove_reasoning = None
    m.system_prompt_prefix = None
    # ensure accepts_settings is a list so membership checks and append() succeed
    m.accepts_settings = []
    return m


def test_apply_generic_gpt4_turbo_round_010():
    m = _make_bare_model()
    # exercise the branch that matches 'gpt-4-turbo' (lines ~499-503)
    m.apply_generic_model_settings("gpt-4-turbo")

    assert m.edit_format == "udiff", "gpt-4-turbo should set edit_format to 'udiff'"
    assert m.use_repo_map is True
    assert m.send_undo_reply is True


def test_apply_generic_qwq_32b_round_010():
    m = _make_bare_model()
    # 'qwq' and '32b' and not 'preview' should set several fields (lines ~562-570)
    m.apply_generic_model_settings("company-qwq-32b")

    assert m.edit_format == "diff"
    assert m.editor_edit_format == "editor-diff"
    assert m.use_repo_map is True
    assert m.reasoning_tag == "think"
    assert m.examples_as_sys_msg is True
    # use_temperature set to numeric 0.6
    assert isinstance(m.use_temperature, float) and abs(m.use_temperature - 0.6) < 1e-9
    # extra_params should be a dict with top_p==0.95
    assert isinstance(m.extra_params, dict) and m.extra_params.get("top_p") == 0.95


def test_apply_generic_qwen3_235b_round_010():
    m = _make_bare_model()
    # triggers the qwen3 + 235b branch (lines ~572-578)
    m.apply_generic_model_settings("qwen3-235b")

    assert m.edit_format == "diff"
    assert m.use_repo_map is True
    assert m.system_prompt_prefix == "/no_think"
    assert isinstance(m.use_temperature, float) and abs(m.use_temperature - 0.7) < 1e-9
    # ensure extra_params contains the expected keys/values
    assert isinstance(m.extra_params, dict)
    assert m.extra_params.get("top_p") == 0.8
    assert m.extra_params.get("top_k") == 20
    assert m.extra_params.get("min_p") == 0.0


def test_apply_generic_last_segment_gpt5_round_010():
    m = _make_bare_model()
    # last_segment logic: the last slash-separated part is matched (lines ~446-452)
    m.accepts_settings = []
    m.apply_generic_model_settings("prefix/path/gpt-5")

    assert m.use_temperature is False
    assert m.edit_format == "diff"
    # 'reasoning_effort' should have been appended if missing
    assert "reasoning_effort" in m.accepts_settings


def test_apply_generic_final_diff_fallback_round_010():
    # If nothing matches earlier, but edit_format already 'diff', final block sets use_repo_map True
    m = _make_bare_model()
    m.edit_format = "diff"
    # choose a model string that doesn't match any special-case branches
    m.apply_generic_model_settings("some-unknown-model-xyz")

    assert m.use_repo_map is True
