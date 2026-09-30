# file: rdagent/scenarios/data_science/proposal/exp_gen/proposal.py:1056-1156
# asked: {"lines": [1065, 1066, 1068, 1070, 1071, 1072, 1074, 1076, 1077, 1078, 1079, 1081, 1082, 1083, 1089, 1091, 1092, 1095, 1097, 1098, 1099, 1101, 1102, 1106, 1107, 1109, 1110, 1111, 1112, 1113, 1114, 1117, 1118, 1120, 1121, 1122, 1123, 1124, 1125, 1128, 1130, 1131, 1132, 1134, 1135, 1136, 1137, 1140, 1141, 1142, 1143, 1146, 1147, 1148, 1149, 1150, 1153, 1154, 1155, 1156], "branches": [[1089, 1091], [1089, 1095], [1098, 1099], [1098, 1101], [1107, 1109], [1107, 1117]]}
# gained: {"lines": [1065, 1066, 1068, 1070, 1071, 1072, 1074, 1076, 1077, 1078, 1079, 1081, 1082, 1083, 1089, 1091, 1092, 1095, 1097, 1098, 1099, 1101, 1102, 1106, 1107, 1109, 1110, 1111, 1112, 1113, 1114, 1117, 1118, 1120, 1121, 1122, 1123, 1124, 1125, 1128, 1130, 1131, 1132, 1134, 1135, 1136, 1137, 1140, 1141, 1142, 1143, 1146, 1147, 1148, 1149, 1150, 1153, 1154, 1155, 1156], "branches": [[1089, 1091], [1089, 1095], [1098, 1099], [1098, 1101], [1107, 1109], [1107, 1117]]}

import json
import datetime
from types import SimpleNamespace

import pandas as pd
import pytest
import importlib

# target module
MOD = importlib.import_module("rdagent.scenarios.data_science.proposal.exp_gen.proposal")
DSProposalV2ExpGen = MOD.DSProposalV2ExpGen
HypothesisComponent = MOD.HypothesisComponent


def make_timer(remain_seconds: int, total_seconds: int):
    class TimerObj:
        def remain_time(self_inner):
            return datetime.timedelta(seconds=remain_seconds)

    # all_duration used as an object with total_seconds method
    class AllDuration:
        def total_seconds(self_inner):
            return total_seconds

    return TimerObj(), AllDuration()


def make_trace_with_search_and_sota(has_sota: bool, running_time_seconds_list, decision_list):
    """
    Create a fake trace object with:
    - retrieve_search_list() returning list of tuples (exp_like, fb_like) where exp_like.running_info.running_time exists
    - optionally sota_exp_to_submit with a DataFrame result
    - scen with competition attribute
    """
    class RunningInfo:
        def __init__(self, running_time):
            self.running_time = running_time

    class ExpLike:
        def __init__(self, running_time):
            self.running_info = RunningInfo(running_time)

    class FbLike:
        def __init__(self, decision):
            self.decision = decision

    pairs = []
    for rt, dec in zip(running_time_seconds_list, decision_list):
        pairs.append((ExpLike(rt), FbLike(dec)))

    trace = SimpleNamespace()
    trace.retrieve_search_list = lambda search_type="ancestors": pairs
    # scen with competition
    trace.scen = SimpleNamespace(competition="dummy_competition")
    if has_sota:
        # Create a DataFrame with index 'ensemble' and one value
        df = pd.DataFrame([[0.456]], index=["ensemble"])
        trace.sota_exp_to_submit = SimpleNamespace(result=df)
    else:
        trace.sota_exp_to_submit = None
    return trace


@pytest.fixture(autouse=True)
def patch_globals(monkeypatch):
    """
    Patch global dependencies used in hypothesis_select_with_llm:
    - RD_Agent_TIMER_wrapper.timer.remain_time and .all_duration
    - DS_RD_SETTING attributes
    - T(...) .r(...) to return simple strings
    - APIBackend.supports_response_schema and APIBackend.build_messages_and_create_chat_completion
    Ensure each test can override supports_response_schema and build_messages if desired.
    """
    # Default timer values (can be overridden in tests by resetting attributes)
    timer_obj, all_dur = make_timer(remain_seconds=600, total_seconds=3600 * 2)  # remain 10min, total 2 hours
    # Provide an object with 'timer' attribute to monkeypatch into module
    monkeypatch.setattr(MOD, "RD_Agent_TIMER_wrapper", SimpleNamespace(timer=SimpleNamespace(remain_time=timer_obj.remain_time, all_duration=all_dur)))

    # DS_RD_SETTING with needed attrs
    monkeypatch.setattr(MOD, "DS_RD_SETTING", SimpleNamespace(ratio_merge_or_ensemble=0.5, merge_hours=1))

    # T(...) -> object with r method returning string (accepts kwargs)
    class Tobj:
        def __init__(self, key):
            self.key = key

        def r(self, **kwargs):
            return f"TEMPLATE:{self.key}:{json.dumps(kwargs, default=str)}"

    monkeypatch.setattr(MOD, "T", lambda key: Tobj(key))

    # Default APIBackend supports_response_schema -> False, and build_messages... returns appropriate json
    class FakeAPI:
        def __init__(self):
            self._supports = False

        def supports_response_schema(self):
            return self._supports

        def build_messages_and_create_chat_completion(self, user_prompt, system_prompt, response_format, json_target_type):
            # return valid JSON string matching HypothesisComponent and hypothesis present
            return json.dumps({"component": HypothesisComponent.Model.value, "hypothesis": "test-hypo"})

    monkeypatch.setattr(MOD, "APIBackend", FakeAPI)

    yield
    # monkeypatch fixture will undo changes


def test_hypothesis_select_with_llm_sota_and_extra_hypo(monkeypatch):
    """
    Test the branch where:
    - trace has sota_exp_to_submit (sota_flag True)
    - _llm_select_extra_hypo returns non-empty -> _prob_dis_torch is called
    - APIBackend.supports_response_schema is False
    """
    # Create a minimal scen object required by ExpGen.__init__
    fake_scen = SimpleNamespace(real_full_timeout=lambda: 3600 * 4)

    # Create instance of DSProposalV2ExpGen with scen
    gen = DSProposalV2ExpGen(fake_scen)

    # Monkeypatch instance methods that would normally access complex internal state
    called = {"prob": False, "get_current": False}

    def fake_get_current_exp_score_list(trace, competition):
        called["get_current"] = True
        # return tuple (score_list, path_length)
        return [0.1, 0.2], 3

    def fake_llm_select_extra_hypo(trace):
        # Return a non-empty list to trigger _prob_dis_torch call
        return [("extra-h1", 0.2), ("extra-h2", 0.8)]

    def fake_prob_dis_torch(current_sota_score_in_current_trace, extra_hypo_l, hypothesis_candidates, competition, path_length):
        called["prob"] = True
        # Just return a list of selected extras
        return ["extra-h2"]

    monkeypatch.setattr(gen, "_get_current_exp_score_list", fake_get_current_exp_score_list)
    monkeypatch.setattr(gen, "_llm_select_extra_hypo", fake_llm_select_extra_hypo)
    monkeypatch.setattr(gen, "_prob_dis_torch", fake_prob_dis_torch)

    # Provide a trace with some running times (include one successful decision True)
    trace = make_trace_with_search_and_sota(has_sota=True, running_time_seconds_list=[3600, 1800], decision_list=[True, False])

    # Call the function
    hypothesis_candidates = {"a": 1}
    result = gen.hypothesis_select_with_llm(
        scenario_desc="scenario",
        exp_feedback_list_desc="feedback",
        sota_exp_desc="sota",
        hypothesis_candidates=hypothesis_candidates,
        trace=trace,
    )

    # Assertions: result is a dict with expected keys; internal helpers were called
    assert isinstance(result, dict)
    assert result["component"] in {m.value for m in HypothesisComponent}
    assert result["hypothesis"] == "test-hypo"
    assert called["prob"] is True
    assert called["get_current"] is True


def test_hypothesis_select_with_llm_no_sota_no_extra_hypo_supports_schema(monkeypatch):
    """
    Test the branch where:
    - trace has no sota_exp_to_submit (sota_flag False)
    - _llm_select_extra_hypo returns empty list -> selected_extra_hypo_l becomes None
    - APIBackend.supports_response_schema is True to exercise response_format path
    - _get_current_exp_score_list should NOT be called
    """
    # Make APIBackend.supports_response_schema True by setting the class in module accordingly
    class APIWithSchema:
        def __init__(self):
            self._supports = True

        def supports_response_schema(self):
            return True

        def build_messages_and_create_chat_completion(self, user_prompt, system_prompt, response_format, json_target_type):
            # Return a valid JSON string; still acceptable to be parsed
            return json.dumps({"component": HypothesisComponent.Ensemble.value, "hypothesis": "hypo-schema"})

    monkeypatch.setattr(MOD, "APIBackend", APIWithSchema)

    fake_scen = SimpleNamespace(real_full_timeout=lambda: 3600 * 1)

    gen = DSProposalV2ExpGen(fake_scen)

    called = {"prob": False, "get_current": False}

    def fake_get_current_exp_score_list(trace, competition):
        called["get_current"] = True
        return [], 0

    def fake_llm_select_extra_hypo(trace):
        # Return empty list to trigger path where selected_extra_hypo_l is None
        return []

    def fake_prob_dis_torch(*args, **kwargs):
        called["prob"] = True
        return []

    monkeypatch.setattr(gen, "_get_current_exp_score_list", fake_get_current_exp_score_list)
    monkeypatch.setattr(gen, "_llm_select_extra_hypo", fake_llm_select_extra_hypo)
    monkeypatch.setattr(gen, "_prob_dis_torch", fake_prob_dis_torch)

    # Create a trace without sota and with no successful decisions
    trace = make_trace_with_search_and_sota(has_sota=False, running_time_seconds_list=[100, 200], decision_list=[False, False])

    hypothesis_candidates = {"b": 2}
    result = gen.hypothesis_select_with_llm(
        scenario_desc="sc2",
        exp_feedback_list_desc="fb2",
        sota_exp_desc="sota2",
        hypothesis_candidates=hypothesis_candidates,
        trace=trace,
    )

    # Assertions
    assert isinstance(result, dict)
    assert result["component"] in {m.value for m in HypothesisComponent}
    assert result["hypothesis"] == "hypo-schema"
    # Since no sota, get_current_exp_score_list should not be called
    assert called["get_current"] is False
    # prob should not be called because extra hypo list empty
    assert called["prob"] is False
