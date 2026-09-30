# file: aider/models.py:421-583
# asked: {"lines": [433, 434, 435, 436, 437, 440, 441, 442, 443, 444, 448, 449, 450, 451, 452, 500, 501, 502, 503, 523, 524, 525, 526, 527, 528, 563, 564, 565, 566, 567, 568, 569, 570, 573, 574, 575, 576, 577, 578, 582, 583], "branches": [[428, 430], [432, 433], [439, 440], [447, 448], [450, 451], [450, 452], [473, 475], [499, 500], [515, 523], [526, 527], [526, 528], [535, 537], [562, 563], [572, 573], [581, 582]]}
# gained: {"lines": [433, 434, 435, 436, 437, 440, 441, 442, 443, 444, 448, 449, 450, 451, 452, 500, 501, 502, 503, 523, 524, 525, 526, 527, 528, 563, 564, 565, 566, 567, 568, 569, 570, 573, 574, 575, 576, 577, 578, 582, 583], "branches": [[432, 433], [439, 440], [447, 448], [450, 451], [499, 500], [515, 523], [526, 527], [562, 563], [572, 573], [581, 582]]}

import types
import pytest

from aider import models


def make_bare_model():
    """
    Create a Model instance without running __init__, then set the fields
    that apply_generic_model_settings expects to exist.
    """
    m = object.__new__(models.Model)
    # Set defaults similar to ModelSettings dataclass
    m.name = None
    m.edit_format = "whole"
    m.weak_model_name = None
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
    m.accepts_settings = []
    return m


def test_o3_mini_adds_reasoning_effort_and_sets_format_and_prefix():
    m = make_bare_model()
    # Ensure accepts_settings starts empty
    assert m.accepts_settings == []
    # Call the method with a string that contains "/o3-mini"
    res = m.apply_generic_model_settings("some/path/o3-mini")
    # The method returns None; primary effect is side-effects on attributes
    assert res is None
    assert m.edit_format == "diff"
    assert m.use_repo_map is True
    assert m.use_temperature is False
    # system_prompt_prefix set to "Formatting re-enabled. "
    assert m.system_prompt_prefix == "Formatting re-enabled. "
    # reasoning_effort must be appended
    assert "reasoning_effort" in m.accepts_settings


def test_gpt_4_1_mini_sets_diff_and_sys_reminder_and_examples_flag():
    m = make_bare_model()
    m.accepts_settings = []
    res = m.apply_generic_model_settings("gpt-4.1-mini")
    assert res is None
    assert m.edit_format == "diff"
    assert m.use_repo_map is True
    assert m.reminder == "sys"
    assert m.examples_as_sys_msg is False


def test_gpt_4_1_sets_diff_and_sys_reminder_and_examples_flag():
    m = make_bare_model()
    m.accepts_settings = []
    res = m.apply_generic_model_settings("gpt-4.1")
    assert res is None
    assert m.edit_format == "diff"
    assert m.use_repo_map is True
    assert m.reminder == "sys"
    assert m.examples_as_sys_msg is False


def test_gpt_5_last_segment_disables_temperature_and_appends_reasoning_effort():
    m = make_bare_model()
    m.accepts_settings = []
    # put gpt-5 as last segment of the model string
    res = m.apply_generic_model_settings("provider/x/gpt-5")
    assert res is None
    assert m.use_temperature is False
    assert m.edit_format == "diff"
    assert "reasoning_effort" in m.accepts_settings


def test_o1_sets_multiple_flags_and_appends_reasoning_effort():
    m = make_bare_model()
    m.accepts_settings = []
    # model contains "/o1"
    res = m.apply_generic_model_settings("prefix/o1")
    assert res is None
    assert m.edit_format == "diff"
    assert m.use_repo_map is True
    assert m.use_temperature is False
    assert m.streaming is False
    assert m.system_prompt_prefix == "Formatting re-enabled. "
    assert "reasoning_effort" in m.accepts_settings


def test_gpt_4_turbo_sets_udiff_and_send_undo_reply():
    m = make_bare_model()
    m.accepts_settings = []
    res = m.apply_generic_model_settings("gpt-4-turbo-x")
    assert res is None
    assert m.edit_format == "udiff"
    assert m.use_repo_map is True
    assert m.send_undo_reply is True


def test_sonnet_4_5_appends_thinking_tokens_and_sets_examples_false():
    m = make_bare_model()
    m.accepts_settings = []
    res = m.apply_generic_model_settings("sonnet-4-5")
    assert res is None
    assert m.edit_format == "diff"
    assert m.use_repo_map is True
    assert m.examples_as_sys_msg is False
    assert "thinking_tokens" in m.accepts_settings


def test_3_7_sonnet_sets_examples_and_appends_thinking_tokens():
    m = make_bare_model()
    m.accepts_settings = []
    res = m.apply_generic_model_settings("3-7-sonnet")
    assert res is None
    assert m.edit_format == "diff"
    assert m.use_repo_map is True
    assert m.examples_as_sys_msg is True
    assert m.reminder == "user"
    assert "thinking_tokens" in m.accepts_settings


def test_qwq_32b_sets_editor_edit_format_reasoning_and_extra_params():
    m = make_bare_model()
    m.accepts_settings = []
    res = m.apply_generic_model_settings("vendor_qwq-32b")
    assert res is None
    assert m.edit_format == "diff"
    assert m.editor_edit_format == "editor-diff"
    assert m.use_repo_map is True
    assert m.reasoning_tag == "think"
    assert m.examples_as_sys_msg is True
    # use_temperature set to a float
    assert pytest.approx(m.use_temperature, rel=1e-6) == 0.6
    assert isinstance(m.extra_params, dict)
    assert m.extra_params.get("top_p") == pytest.approx(0.95, rel=1e-6)


def test_qwen3_235b_sets_system_prefix_temperature_and_extra_params():
    m = make_bare_model()
    m.accepts_settings = []
    res = m.apply_generic_model_settings("qwen3-235b")
    assert res is None
    assert m.edit_format == "diff"
    assert m.use_repo_map is True
    assert m.system_prompt_prefix == "/no_think"
    assert pytest.approx(m.use_temperature, rel=1e-6) == 0.7
    assert isinstance(m.extra_params, dict)
    # check keys and a sample value
    assert m.extra_params.get("top_p") == pytest.approx(0.8, rel=1e-6)
    assert m.extra_params.get("top_k") == 20
    assert "min_p" in m.extra_params


def test_default_edit_format_diff_enables_repo_map_on_exit():
    # If edit_format already diff and model doesn't match any condition,
    # apply_generic_model_settings should set use_repo_map True at the end.
    m = make_bare_model()
    m.accepts_settings = []
    m.edit_format = "diff"
    # Use a model string that won't match any other branch
    res = m.apply_generic_model_settings("this-model-does-not-match-any-rule")
    assert res is None
    assert m.use_repo_map is True
