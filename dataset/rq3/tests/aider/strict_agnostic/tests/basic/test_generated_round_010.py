import pytest

from aider.models import Model


def _make_bare_model():
    # Instantiate without calling __init__ to avoid side effects. Tests will
    # manually set the attributes that apply_generic_model_settings expects.
    m = object.__new__(Model)
    # default baseline attributes used/checked by apply_generic_model_settings
    m.edit_format = None
    m.use_repo_map = False
    m.use_temperature = True
    m.system_prompt_prefix = None
    m.accepts_settings = []
    m.reminder = None
    m.examples_as_sys_msg = None
    m.send_undo_reply = False
    m.streaming = True
    m.use_system_prompt = True
    m.reasoning_tag = None
    m.editor_edit_format = None
    m.extra_params = None
    return m


def test_o3_mini_round_010():
    m = _make_bare_model()
    # exercise the "/o3-mini" branch
    m.apply_generic_model_settings("vendor/o3-mini-v1")
    assert m.edit_format == "diff"
    assert m.use_repo_map is True
    assert m.use_temperature is False
    assert m.system_prompt_prefix == "Formatting re-enabled. "
    # reasoning_effort should have been appended exactly once
    assert "reasoning_effort" in m.accepts_settings


def test_gpt_4_1_mini_round_010():
    m = _make_bare_model()
    m.apply_generic_model_settings("gpt-4.1-mini")
    assert m.edit_format == "diff"
    assert m.use_repo_map is True
    assert m.reminder == "sys"
    assert m.examples_as_sys_msg is False


def test_gpt_4_1_round_010():
    m = _make_bare_model()
    m.apply_generic_model_settings("something-gpt-4.1-release")
    assert m.edit_format == "diff"
    assert m.use_repo_map is True
    assert m.reminder == "sys"
    assert m.examples_as_sys_msg is False


def test_gpt_5_last_segment_round_010():
    m = _make_bare_model()
    # last segment is gpt-5 -> triggers reasoning_effort append path
    m.apply_generic_model_settings("org/models/gpt-5")
    assert m.use_temperature is False
    assert m.edit_format == "diff"
    assert "reasoning_effort" in m.accepts_settings


def test_gpt_4_turbo_round_010():
    m = _make_bare_model()
    m.apply_generic_model_settings("gpt-4-turbo")
    # gpt-4-turbo branch sets udiff and sends undo reply
    assert m.edit_format == "udiff"
    assert m.use_repo_map is True
    assert m.send_undo_reply is True


def test_sonnet_group_thinking_tokens_round_010():
    m = _make_bare_model()
    # one of the multiple names in the group; triggers thinking_tokens append
    m.apply_generic_model_settings("sonnet-4-5")
    assert m.edit_format == "diff"
    assert m.use_repo_map is True
    assert m.examples_as_sys_msg is False
    assert "thinking_tokens" in m.accepts_settings


def test_3_7_sonnet_round_010():
    m = _make_bare_model()
    m.apply_generic_model_settings("vendor/3-7-sonnet")
    assert m.edit_format == "diff"
    assert m.use_repo_map is True
    assert m.examples_as_sys_msg is True
    assert m.reminder == "user"
    assert "thinking_tokens" in m.accepts_settings


def test_qwq_32b_round_010():
    m = _make_bare_model()
    # ensure 'preview' is NOT present
    m.apply_generic_model_settings("vendor/qwq-32b")
    assert m.edit_format == "diff"
    assert m.editor_edit_format == "editor-diff"
    assert m.use_repo_map is True
    assert m.reasoning_tag == "think"
    assert m.examples_as_sys_msg is True
    # floating-point equality check for deterministic value
    assert m.use_temperature == 0.6
    assert isinstance(m.extra_params, dict) and m.extra_params.get("top_p") == 0.95


def test_qwen3_235b_round_010():
    m = _make_bare_model()
    m.apply_generic_model_settings("some/qwen3-235b")
    assert m.edit_format == "diff"
    assert m.use_repo_map is True
    assert m.system_prompt_prefix == "/no_think"
    assert m.use_temperature == 0.7
    # extra_params should be a dict with expected keys and values
    assert isinstance(m.extra_params, dict)
    assert m.extra_params.get("top_p") == 0.8
    assert m.extra_params.get("top_k") == 20
    assert m.extra_params.get("min_p") == 0.0


def test_default_edit_format_diff_sets_use_repo_map_round_010():
    # If edit_format already equals "diff" and no branch matches, the final
    # default at the end of the function should set use_repo_map True.
    m = _make_bare_model()
    m.edit_format = "diff"
    # choose a model string that doesn't match any special-case checks above
    m.apply_generic_model_settings("custom-nonmatching-model")
    assert m.use_repo_map is True
