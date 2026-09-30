import importlib
import json
from types import SimpleNamespace

import pytest

# Import the module under test
submit = importlib.import_module(
    "rdagent.scenarios.data_science.proposal.exp_gen.select.submit"
)

# Helper fake template loader
class FakeT:
    def __init__(self, key):
        self.key = key

    def r(self, **kwargs):
        # Return a deterministic string that includes any provided kwargs for visibility
        if "scenario" in kwargs:
            return f"system_prompt_for:{kwargs['scenario']}"
        if "historical_sota_exp_with_desc_and_scores" in kwargs:
            return kwargs["historical_sota_exp_with_desc_and_scores"]
        # generic fallback
        return "fake_prompt"


class DummyBackend:
    def __init__(self, token_return=1, chat_return='{"selected_SOTA_idx": 1}'):
        self._token = token_return
        self._chat = chat_return

    def build_messages_and_calculate_token(self, user_prompt, system_prompt):
        # deterministic token size
        return self._token

    def build_messages_and_create_chat_completion(
        self, user_prompt, system_prompt, json_mode, json_target_type
    ):
        # Return stringified JSON as the real implementation would
        return self._chat


@pytest.fixture(autouse=True)
def patch_module_dependencies(monkeypatch):
    """Patch out external dependencies from the submit module to keep tests deterministic.

    This fixture runs automatically for each test in this module.
    """
    # Patch templating helper T used to build prompts
    monkeypatch.setattr(submit, "T", lambda key: FakeT(key))

    # Provide a safe default LLM_SETTINGS chat token limit; tests can override if needed
    monkeypatch.setattr(submit, "LLM_SETTINGS", SimpleNamespace(chat_token_limit=1000))

    yield


def make_trace():
    # Minimal trace with scen.get_scenario_all_desc used by the code
    return SimpleNamespace(scen=SimpleNamespace(get_scenario_all_desc=lambda: "scenario_description"))


class ExpObj:
    def __init__(self, result):
        # store the raw result used to create a DataFrame in the function under test
        self.result = result


def test_no_candidates_round_062():
    """When collect_sota_candidates returns empty list, function should return None."""
    selector = submit.AutoSOTAexpSelector()

    # Patch collect_sota_candidates to return no candidates
    selector.collect_sota_candidates = lambda trace: []

    result = selector.get_sota_exp_to_submit(make_trace())
    assert result is None


def test_one_candidate_round_062():
    """When there's exactly one candidate, it should be selected directly."""
    selector = submit.AutoSOTAexpSelector()

    exp = ExpObj(result=None)  # result is irrelevant for the single-candidate shortcut
    selector.collect_sota_candidates = lambda trace: [(exp, "fb")]

    chosen = selector.get_sota_exp_to_submit(make_trace())
    assert chosen is exp


def test_multiple_candidates_with_skipped_result_and_valid_selection_round_062():
    """Covers loop that skips experiments with result=None and uses LLM selection to pick a valid index."""
    selector = submit.AutoSOTAexpSelector()

    # exp1 has a valid result (DataFrame will be built from this dict)
    exp1 = ExpObj(result={"c1": {"ensemble": 0.90}})
    # exp2 will be skipped because result is None
    exp2 = ExpObj(result=None)
    # exp3 has a valid result
    exp3 = ExpObj(result={"c1": {"ensemble": 0.95}})

    sota_list = [(exp1, "fb1"), (exp2, "fb2"), (exp3, "fb3")]
    selector.collect_sota_candidates = lambda trace: sota_list

    # Patch APIBackend to return a valid selection: pick the 3rd experiment
    submit.APIBackend = lambda: DummyBackend(token_return=1, chat_return=json.dumps({"selected_SOTA_idx": 3}))

    chosen = selector.get_sota_exp_to_submit(make_trace())
    assert chosen is exp3


def test_multiple_candidates_with_invalid_selection_fallback_round_062():
    """If LLM returns an invalid index, fallback to the latest SOTA (last item in the list)."""
    selector = submit.AutoSOTAexpSelector()

    exp1 = ExpObj(result={"c1": {"ensemble": 0.80}})
    exp2 = ExpObj(result={"c1": {"ensemble": 0.85}})
    sota_list = [(exp1, "fb1"), (exp2, "fb2")]
    selector.collect_sota_candidates = lambda trace: sota_list

    # LLM returns an out-of-range index -> expect fallback to last experiment
    submit.APIBackend = lambda: DummyBackend(token_return=1, chat_return=json.dumps({"selected_SOTA_idx": 999}))

    chosen = selector.get_sota_exp_to_submit(make_trace())
    assert chosen is exp2


def test_token_limit_break_stops_adding_experiments_round_062():
    """If token size reaches limit during building prompts, the loop breaks and selection still proceeds."""
    selector = submit.AutoSOTAexpSelector()

    exp1 = ExpObj(result={"c1": {"ensemble": 0.70}})
    exp2 = ExpObj(result={"c1": {"ensemble": 0.75}})
    sota_list = [(exp1, "fb1"), (exp2, "fb2")]
    selector.collect_sota_candidates = lambda trace: sota_list

    # Make token limit small and APIBackend.calculate return equal to limit to trigger the break path
    submit.LLM_SETTINGS = SimpleNamespace(chat_token_limit=2)
    submit.APIBackend = lambda: DummyBackend(token_return=2, chat_return=json.dumps({"selected_SOTA_idx": 1}))

    chosen = selector.get_sota_exp_to_submit(make_trace())
    # Even if build loop breaks early, LLM can still pick first experiment -> verify returned
    assert chosen is exp1
