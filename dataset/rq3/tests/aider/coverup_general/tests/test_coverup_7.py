# file: aider/models.py:421-583
# asked: {"lines": [433, 434, 435, 436, 437, 440, 441, 442, 443, 444, 448, 449, 450, 451, 452, 500, 501, 502, 503, 523, 524, 525, 526, 527, 528, 563, 564, 565, 566, 567, 568, 569, 570, 573, 574, 575, 576, 577, 578, 582, 583], "branches": [[428, 430], [432, 433], [439, 440], [447, 448], [450, 451], [450, 452], [473, 475], [499, 500], [515, 523], [526, 527], [526, 528], [535, 537], [562, 563], [572, 573], [581, 582]]}
# gained: {"lines": [433, 434, 435, 436, 437, 440, 441, 442, 443, 444, 448, 449, 450, 451, 452, 500, 501, 502, 503, 523, 524, 525, 526, 527, 528, 563, 564, 565, 566, 567, 568, 569, 570, 573, 574, 575, 576, 577, 578, 582, 583], "branches": [[432, 433], [439, 440], [447, 448], [450, 451], [499, 500], [515, 523], [526, 527], [562, 563], [572, 573], [581, 582]]}

import pytest
from aider import models
from aider.models import Model


@pytest.fixture(autouse=True)
def stub_model_init_helpers(monkeypatch):
    """
    Monkeypatch Model methods that would access external state so tests can
    instantiate Model safely and focus on apply_generic_model_settings behavior.
    This fixture is autouse for all tests in this module.
    """
    # Stub get_model_info to return a benign dict
    monkeypatch.setattr(Model, "get_model_info", lambda self, model: {"max_input_tokens": 1024})

    # Stub validate_environment to return expected structure
    monkeypatch.setattr(Model, "validate_environment", lambda self: {"missing_keys": None, "keys_in_environment": None})

    # Provide a configure_model_settings that initializes the dataclass-like fields
    def fake_configure(self, model):
        # set all fields that apply_generic_model_settings may read/write
        self.edit_format = "whole"
        self.weak_model_name = None
        self.use_repo_map = False
        self.send_undo_reply = False
        self.lazy = False
        self.overeager = False
        self.reminder = "user"
        self.examples_as_sys_msg = False
        self.extra_params = None
        self.cache_control = False
        self.caches_by_default = False
        self.use_system_prompt = True
        self.use_temperature = True
        self.streaming = True
        self.editor_model_name = None
        self.editor_edit_format = None
        self.reasoning_tag = None
        self.remove_reasoning = None
        self.system_prompt_prefix = None
        self.accepts_settings = []
    monkeypatch.setattr(Model, "configure_model_settings", fake_configure)

    # Prevent weak/editor model helpers from doing anything unexpected
    monkeypatch.setattr(Model, "get_weak_model", lambda self, provided: setattr(self, "weak_model_name", None))
    monkeypatch.setattr(Model, "get_editor_model", lambda self, provided, fmt: setattr(self, "editor_model_name", None))

    yield


def test_o3_mini_appends_reasoning_effort_and_sets_flags():
    m = Model("vendor/o3-mini")
    # apply_generic_model_settings returns early after setting fields
    m.apply_generic_model_settings("vendor/o3-mini")
    assert m.edit_format == "diff"
    assert m.use_repo_map is True
    assert m.use_temperature is False
    assert m.system_prompt_prefix == "Formatting re-enabled. "
    assert "reasoning_effort" in m.accepts_settings


def test_gpt_4_1_mini_and_gpt_4_1_setters():
    m1 = Model("org/gpt-4.1-mini")
    m1.apply_generic_model_settings("org/gpt-4.1-mini")
    assert m1.edit_format == "diff"
    assert m1.use_repo_map is True
    assert m1.reminder == "sys"
    assert m1.examples_as_sys_msg is False

    m2 = Model("org/gpt-4.1")
    m2.apply_generic_model_settings("org/gpt-4.1")
    assert m2.edit_format == "diff"
    assert m2.use_repo_map is True
    assert m2.reminder == "sys"
    assert m2.examples_as_sys_msg is False


def test_gpt5_last_segment_appends_reasoning_effort():
    m = Model("some/path/gpt-5")
    m.apply_generic_model_settings("some/path/gpt-5")
    assert m.use_temperature is False
    assert m.edit_format == "diff"
    assert "reasoning_effort" in m.accepts_settings


def test_o1_sets_streaming_false_and_appends_reasoning_effort():
    m = Model("prefix/o1")
    m.apply_generic_model_settings("prefix/o1")
    assert m.edit_format == "diff"
    assert m.use_repo_map is True
    assert m.use_temperature is False
    assert m.streaming is False
    assert m.system_prompt_prefix == "Formatting re-enabled. "
    assert "reasoning_effort" in m.accepts_settings


def test_gpt4_turbo_sets_udiff_and_send_undo():
    m = Model("gpt-4-turbo")
    m.apply_generic_model_settings("gpt-4-turbo")
    assert m.edit_format == "udiff"
    assert m.use_repo_map is True
    assert m.send_undo_reply is True


def test_sonnet_and_3_7_sonnet_append_thinking_tokens():
    m_sonnet = Model("sonnet-4-5")
    m_sonnet.apply_generic_model_settings("sonnet-4-5")
    assert m_sonnet.edit_format == "diff"
    assert m_sonnet.use_repo_map is True
    assert m_sonnet.examples_as_sys_msg is False
    assert "thinking_tokens" in m_sonnet.accepts_settings

    m_3_7 = Model("vendor/3-7-sonnet")
    m_3_7.apply_generic_model_settings("vendor/3-7-sonnet")
    assert m_3_7.edit_format == "diff"
    assert m_3_7.use_repo_map is True
    assert m_3_7.examples_as_sys_msg is True
    assert m_3_7.reminder == "user"
    assert "thinking_tokens" in m_3_7.accepts_settings


def test_qwq_and_qwen3_settings():
    m_qwq = Model("company/qwq-32b")
    m_qwq.apply_generic_model_settings("company/qwq-32b")
    assert m_qwq.edit_format == "diff"
    assert m_qwq.editor_edit_format == "editor-diff"
    assert m_qwq.use_repo_map is True
    assert m_qwq.reasoning_tag == "think"
    assert m_qwq.examples_as_sys_msg is True
    assert m_qwq.use_temperature == 0.6
    assert m_qwq.extra_params == dict(top_p=0.95)

    m_qwen3 = Model("org/qwen3-235b")
    m_qwen3.apply_generic_model_settings("org/qwen3-235b")
    assert m_qwen3.edit_format == "diff"
    assert m_qwen3.use_repo_map is True
    assert m_qwen3.system_prompt_prefix == "/no_think"
    assert m_qwen3.use_temperature == 0.7
    assert m_qwen3.extra_params == {"top_p": 0.8, "top_k": 20, "min_p": 0.0}


def test_final_edit_format_diff_sets_use_repo_map_when_no_match():
    # Start with edit_format already 'diff' but use_repo_map False and a model that matches nothing else.
    m = Model("base-model")
    # ensure initial state mimics a previously configured diff without repo map
    m.edit_format = "diff"
    m.use_repo_map = False
    m.accepts_settings = []
    m.apply_generic_model_settings("completely-unmatched-model")
    assert m.use_repo_map is True
