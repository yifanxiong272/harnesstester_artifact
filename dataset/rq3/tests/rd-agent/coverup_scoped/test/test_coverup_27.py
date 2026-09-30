# file: rdagent/scenarios/data_science/proposal/exp_gen/select/submit.py:67-128
# asked: {"lines": [72, 74, 75, 76, 78, 79, 80, 82, 85, 86, 87, 88, 89, 90, 91, 92, 93, 95, 96, 99, 100, 101, 103, 104, 105, 107, 110, 112, 113, 114, 115, 116, 118, 119, 122, 123, 124, 125, 127, 128], "branches": [[74, 75], [74, 78], [78, 79], [78, 82], [87, 88], [87, 110], [88, 87], [88, 89], [103, 104], [103, 107], [122, 123], [122, 127]]}
# gained: {"lines": [72, 74, 75, 76, 78, 79, 80, 82, 85, 86, 87, 88, 89, 90, 91, 92, 93, 95, 96, 99, 100, 101, 103, 107, 110, 112, 113, 114, 115, 116, 118, 119, 122, 123, 124, 125, 127, 128], "branches": [[74, 75], [74, 78], [78, 79], [78, 82], [87, 88], [87, 110], [88, 89], [103, 107], [122, 123], [122, 127]]}

import json
import types
import pandas as pd
import importlib
import pytest

# Import the module under test
mod = importlib.import_module("rdagent.scenarios.data_science.proposal.exp_gen.select.submit")
AutoSOTAexpSelector = mod.AutoSOTAexpSelector


class SimpleExp:
    def __init__(self, name, score=None):
        self.name = name
        if score is None:
            # No result
            self.result = None
        else:
            # DataFrame with index 'ensemble' so .loc["ensemble"].iloc[0] works
            self.result = pd.DataFrame([[score]], index=["ensemble"])

    def __repr__(self):
        return f"<SimpleExp {self.name}>"


class DummyScen:
    def get_scenario_all_desc(self):
        return "dummy scenario desc"


class DummyTrace:
    def __init__(self):
        self.scen = DummyScen()


class DummyTObj:
    def __init__(self, key):
        self.key = key

    def r(self, **kwargs):
        # Return different text depending on key to simulate templates
        if "describe.exp" in self.key:
            exp = kwargs.get("exp")
            return f"Description of {exp}"
        if "auto_sota_selector.system" in self.key:
            return "SYSTEM_PROMPT"
        # user prompt case
        if "auto_sota_selector.user" in self.key:
            # return the provided historical string or empty
            return kwargs.get("historical_sota_exp_with_desc_and_scores", "")
        # generic fallback
        return str(kwargs)


def make_fake_T():
    def _T(key):
        return DummyTObj(key)
    return _T


class FakeAPIBackend:
    """
    Fake APIBackend that yields a sequence of token sizes for calculate_token
    and returns a configurable JSON response for chat completion.
    """
    def __init__(self, token_sizes=None, completion_response=None):
        # token_sizes is an iterable or list; we pop from it on each call
        self._token_sizes = list(token_sizes or [])
        self._completion_response = completion_response or json.dumps({})

    def build_messages_and_calculate_token(self, user_prompt, system_prompt):
        # return next token size or 0 if exhausted
        if self._token_sizes:
            return self._token_sizes.pop(0)
        return 0

    def build_messages_and_create_chat_completion(self, user_prompt, system_prompt, json_mode, json_target_type):
        # return the configured JSON string
        return self._completion_response


def make_fake_api_backend_factory(token_sizes, completion_response):
    """
    Returns a factory function that mimics the APIBackend class constructor used in the module.
    The module calls APIBackend() with no args; this returns an object with the methods used.
    """
    def factory():
        return FakeAPIBackend(token_sizes=list(token_sizes), completion_response=completion_response)
    return factory


def test_no_candidates_returns_none(monkeypatch):
    selector = AutoSOTAexpSelector()
    # collect_sota_candidates returns empty
    monkeypatch.setattr(selector, "collect_sota_candidates", lambda trace: [])
    trace = DummyTrace()
    res = selector.get_sota_exp_to_submit(trace)
    assert res is None


def test_single_candidate_selected(monkeypatch):
    selector = AutoSOTAexpSelector()
    exp = SimpleExp("only_one")
    # Return exactly one candidate
    monkeypatch.setattr(selector, "collect_sota_candidates", lambda trace: [(exp, None)])
    trace = DummyTrace()
    res = selector.get_sota_exp_to_submit(trace)
    assert res is exp


def test_multiple_candidates_llm_select_valid(monkeypatch):
    selector = AutoSOTAexpSelector()
    # Two experiments with results so loop will process them
    exp1 = SimpleExp("exp1", score=0.8)
    exp2 = SimpleExp("exp2", score=0.9)
    candidates = [(exp1, None), (exp2, None)]
    monkeypatch.setattr(selector, "collect_sota_candidates", lambda trace: candidates)

    # Patch T in the module to our dummy
    monkeypatch.setattr(mod, "T", make_fake_T())

    # Make LLM_SETTINGS token limit and APIBackend token sizes.
    # token_sizes: first call small (so appended), second call large to trigger break
    monkeypatch.setattr(mod, "LLM_SETTINGS", types.SimpleNamespace(chat_token_limit=500))
    fake_factory = make_fake_api_backend_factory(token_sizes=[10, 999], completion_response=json.dumps({"selected_SOTA_idx": 1}))
    monkeypatch.setattr(mod, "APIBackend", lambda: fake_factory())

    trace = DummyTrace()
    selected = selector.get_sota_exp_to_submit(trace)
    # selected idx 1 -> exp1
    assert selected is exp1


def test_multiple_candidates_llm_invalid_fallback(monkeypatch):
    selector = AutoSOTAexpSelector()
    exp1 = SimpleExp("exp1", score=0.8)
    exp2 = SimpleExp("exp2", score=0.9)
    exp3 = SimpleExp("exp3", score=0.75)
    candidates = [(exp1, None), (exp2, None), (exp3, None)]
    monkeypatch.setattr(selector, "collect_sota_candidates", lambda trace: candidates)

    # Patch T
    monkeypatch.setattr(mod, "T", make_fake_T())

    # Ensure token sizes are small so loop doesn't break prematurely (so prompt includes multiple experiments)
    monkeypatch.setattr(mod, "LLM_SETTINGS", types.SimpleNamespace(chat_token_limit=1000))
    # Return an invalid selection (e.g., out-of-range number) to trigger fallback to last candidate
    fake_factory = make_fake_api_backend_factory(token_sizes=[5, 5, 5], completion_response=json.dumps({"selected_SOTA_idx": 999}))
    monkeypatch.setattr(mod, "APIBackend", lambda: fake_factory())

    trace = DummyTrace()
    selected = selector.get_sota_exp_to_submit(trace)
    # Invalid selection -> fallback to last candidate (exp3)
    assert selected is exp3
