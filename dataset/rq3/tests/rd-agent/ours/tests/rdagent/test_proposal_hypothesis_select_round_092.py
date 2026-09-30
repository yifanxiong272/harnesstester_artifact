import json
from datetime import timedelta
import pandas as pd
import pytest

import rdagent.scenarios.data_science.proposal.exp_gen.proposal as proposal_mod


class FakeTimer:
    def __init__(self, remain_seconds=1800, total_hours=3):
        self._remain = timedelta(seconds=remain_seconds)
        self.all_duration = timedelta(hours=total_hours)

    def remain_time(self):
        return self._remain


class FakeNode:
    def __init__(self, running_time):
        class RI:
            def __init__(self, running_time):
                self.running_time = running_time

        self.running_info = RI(running_time)


class FakeMeta:
    def __init__(self, decision):
        self.decision = decision


class FakeTrace:
    def __init__(self, include_sota=False, sota_value=0.9, competition="comp"):
        # build retrieve_search_list data
        # one successful ancestor with running_time 7200 (2 hours)
        self._search_list = [(FakeNode(7200), FakeMeta(True)), (FakeNode(1800), FakeMeta(False))]
        self.scen = type("S", (), {"competition": competition})()
        if include_sota:
            # create a pandas DataFrame with index 'ensemble' so .loc['ensemble'].iloc[0].round(3) works
            df = pd.DataFrame([[sota_value]], index=["ensemble"])
            self.sota_exp_to_submit = type("Sota", (), {"result": df})()
        else:
            self.sota_exp_to_submit = None

    def retrieve_search_list(self, search_type="ancestors"):
        assert search_type == "ancestors"
        return self._search_list


class FakeAPIBackend:
    def __init__(self, response):
        self._response = response

    def build_messages_and_create_chat_completion(self, *args, **kwargs):
        # Return a JSON string as the real APIBackend would
        return json.dumps(self._response)


class DummyT:
    def __init__(self, _):
        pass

    def r(self, **kwargs):
        # return a deterministic textual prompt regardless of kwargs
        return "SYS_PROMPT: " + json.dumps({k: (str(v) if not isinstance(v, (dict, list)) else v) for k, v in kwargs.items()})


@pytest.fixture(autouse=True)
def patch_globals(monkeypatch):
    # Patch RD_Agent_TIMER_wrapper.timer
    monkeypatch.setattr(proposal_mod.RD_Agent_TIMER_wrapper, "timer", FakeTimer(remain_seconds=1800, total_hours=3), raising=False)

    # Patch DS_RD_SETTING values used in the function
    if hasattr(proposal_mod, "DS_RD_SETTING"):
        monkeypatch.setattr(proposal_mod.DS_RD_SETTING, "ratio_merge_or_ensemble", 0.42, raising=False)
        monkeypatch.setattr(proposal_mod.DS_RD_SETTING, "merge_hours", 6, raising=False)

    # Patch T template resolver
    monkeypatch.setattr(proposal_mod, "T", DummyT)

    yield


def _make_proposal_instance():
    # Provide a fake scen object required by ExpGen.__init__
    fake_scen = type("Scen", (), {"real_full_timeout": lambda self: 7200, "competition": "compX"})()
    inst = proposal_mod.DSProposalV2ExpGen(fake_scen)
    return inst


def test_hypothesis_select_with_llm_sota_and_extra_round_092(monkeypatch):
    """Branch: sota_flag True, extra_hypo non-empty -> calls _prob_dis_torch and _get_current_exp_score_list path."""
    inst = _make_proposal_instance()

    # create trace with sota present
    trace = FakeTrace(include_sota=True, sota_value=0.91234, competition="compA")

    # Patch instance helpers to deterministic returns
    monkeypatch.setattr(proposal_mod.DSProposalV2ExpGen, "_llm_select_extra_hypo", lambda self, t: ["extra_h1", "extra_h2"]) 
    # _prob_dis_torch should be called and return a list of selections
    monkeypatch.setattr(proposal_mod.DSProposalV2ExpGen, "_prob_dis_torch", lambda self, a, b, c, d, e: ["selected_extra_h1"]) 
    # _get_current_exp_score_list returns tuple when sota_flag True
    monkeypatch.setattr(proposal_mod.DSProposalV2ExpGen, "_get_current_exp_score_list", lambda self, t, comp: ([0.8], 2))

    # Ensure supports_response_schema is False to exercise the template fallback path
    inst.supports_response_schema = False

    # Prepare APIBackend to return a valid component and hypothesis
    # use an available HypothesisComponent member name to be valid
    valid_component = next(iter(proposal_mod.HypothesisComponent.__members__.keys()))
    fake_response = {"component": valid_component, "hypothesis": "this is a hypothesis"}
    monkeypatch.setattr(proposal_mod, "APIBackend", lambda *args, **kwargs: FakeAPIBackend(fake_response))

    # Run the method
    result = inst.hypothesis_select_with_llm(
        scenario_desc="scenario",
        exp_feedback_list_desc="fb",
        sota_exp_desc="sota",
        hypothesis_candidates={"a": "b"},
        trace=trace,
    )

    # Assertions: returned dict matches expected and internal assertions passed
    assert isinstance(result, dict)
    assert result["component"] == valid_component
    assert result["hypothesis"] == "this is a hypothesis"


def test_hypothesis_select_with_llm_no_sota_and_no_extra_round_092(monkeypatch):
    """Branch: sota_flag False, extra_hypo empty -> skip _prob_dis_torch and _get_current_exp_score_list false path."""
    inst = _make_proposal_instance()

    # create trace without sota
    trace = FakeTrace(include_sota=False, competition="compB")

    # Patch instance helpers: no extra hypos
    monkeypatch.setattr(proposal_mod.DSProposalV2ExpGen, "_llm_select_extra_hypo", lambda self, t: [])
    # Ensure _get_current_exp_score_list is NOT used in this branch, but patch to defensive value
    monkeypatch.setattr(proposal_mod.DSProposalV2ExpGen, "_get_current_exp_score_list", lambda self, t, comp: ([0.0], 0))

    # Set supports_response_schema True to exercise the other branch for hypothesis_output_format
    inst.supports_response_schema = True

    valid_component = next(iter(proposal_mod.HypothesisComponent.__members__.keys()))
    fake_response = {"component": valid_component, "hypothesis": "h2"}
    monkeypatch.setattr(proposal_mod, "APIBackend", lambda *args, **kwargs: FakeAPIBackend(fake_response))

    # Run the method
    result = inst.hypothesis_select_with_llm(
        scenario_desc="scenario2",
        exp_feedback_list_desc="fb2",
        sota_exp_desc="sota2",
        hypothesis_candidates={"x": "y"},
        trace=trace,
    )

    # Assertions: verify defaulted scores and returned payload
    assert isinstance(result, dict)
    assert result["component"] == valid_component
    assert result["hypothesis"] == "h2"
