import pickle
from pathlib import Path
import types
import builtins
import pytest

from rdagent.scenarios.data_science.proposal.exp_gen.select import submit as submit_mod
from rdagent.scenarios.data_science.proposal.exp_gen.select.submit import evaluate_one_trace


class DummyScen:
    def __init__(self, competition, metric_direction=0):
        self.competition = competition
        self.metric_direction = metric_direction


class DummyTrace:
    def __init__(self, competition, metric_direction=0):
        self.scen = DummyScen(competition, metric_direction)


def _make_pickle_file(path: Path, content: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(content, f)


def test_global_selector_round_010(tmp_path, monkeypatch):
    """
    Covers: selector_name == 'global' branch, competition special-case that flips metric_direction,
    and debug True path where check_hit determines the returned hit boolean.
    """
    # Prepare a trace that triggers the competition special-case
    trace = DummyTrace("detecting-insults-in-social-commentary", metric_direction=0)

    # Patch GlobalSOTASelector to a deterministic dummy with expected method
    class DummyGlobalSelector:
        def __init__(self):
            pass

        def get_sota_exp_to_submit(self, trace_arg):
            # Return a sentinel selected experiment
            return "selected_exp_global"

    monkeypatch.setattr(submit_mod, "GlobalSOTASelector", DummyGlobalSelector)

    # Patch check_hit to observe that it receives our selected experiment and return True
    def fake_check_hit(selected, trace_arg, sota_result):
        assert selected == "selected_exp_global"
        # ensure the special-case in the scen changed direction sign logic upstream didn't crash
        assert trace_arg.scen.metric_direction == 1 or trace_arg.scen.metric_direction == 0
        return True

    monkeypatch.setattr(submit_mod, "check_hit", fake_check_hit)

    # Provide dummy settings for DS_RD_SETTING.local_data_path (not used in this branch)
    dummy_ds = types.SimpleNamespace(local_data_path=str(tmp_path))
    monkeypatch.setattr(submit_mod, "DS_RD_SETTING", dummy_ds)

    # Call under test (debug True -> uses check_hit path)
    competition, hit, sota_exp_stat = evaluate_one_trace(
        selector_name="global",
        trace=trace,
        debug=True,
        only_sample=False,
        sample_code_path="",
        sota_result={},
        experiment="validation",
        log_path=tmp_path,
        sample_rate=0.8,
    )

    assert competition == "detecting-insults-in-social-commentary"
    assert hit is True
    assert sota_exp_stat == ""


def test_validation_selector_round_010(tmp_path, monkeypatch):
    """
    Covers: selector_name == 'validation' branch where Path exists, candidate_exps returned,
    pool path checks for mle_score files (via log_path.rglob), building ValidationSelector,
    and final evaluation of mle_score that yields a gold medal -> sota_exp_stat 'gold'.
    """
    competition = "my_comp"
    # Ensure DS_RD_SETTING.local_data_path/competition exists so Path.exists() is True
    ds_root = tmp_path / "ds_root"
    comp_dir = ds_root / competition
    comp_dir.mkdir(parents=True)

    # Prepare trace
    trace = DummyTrace(competition, metric_direction=0)

    # Patch DS_RD_SETTING
    dummy_ds = types.SimpleNamespace(local_data_path=str(ds_root))
    monkeypatch.setattr(submit_mod, "DS_RD_SETTING", dummy_ds)

    # Prepare quick_selector (BestValidSelector) to return a quick selection (not ultimately used)
    class DummyBestValidQuick:
        def __init__(self, *args, **kwargs):
            pass

        def get_sota_exp_to_submit(self, trace_arg):
            return "quick_choice"

        def collect_sota_candidates(self, trace_arg):
            # Return a single candidate object that the base selector would return
            return ["candidate_exp_1"]

    monkeypatch.setattr(submit_mod, "BestValidSelector", DummyBestValidQuick)

    # Patch try_get_loop_id to map our candidate to loop '1' during pool checking
    def fake_try_get_loop_id(trace_arg, exp_arg):
        # For the pool check stage, return loop id '1'
        if exp_arg == "candidate_exp_1":
            return "1"
        # For later mapping when ValidationSelector is created, return whatever mapping is requested
        return "2"

    monkeypatch.setattr(submit_mod, "try_get_loop_id", fake_try_get_loop_id)

    # Patch extract_json to be identity for whatever pickle contains
    monkeypatch.setattr(submit_mod, "extract_json", lambda x: x)

    # Create a mle_score pickle under Loop_1 for the pool check with any_medal True
    pool_score = {"any_medal": True}
    pool_file = tmp_path / "Loop_1" / "running" / "mle_score" / "score_pool.pkl"
    _make_pickle_file(pool_file, pool_score)

    # Create another mle_score pickle under Loop_2 for the final ValidationSelector check with gold True
    final_score = {"any_medal": True, "gold_medal": True, "silver_medal": False, "bronze_medal": False}
    final_file = tmp_path / "Loop_2" / "running" / "mle_score" / "score_final.pkl"
    _make_pickle_file(final_file, final_score)

    # Define a ValidationSelector dummy that records the candidate mapping and provides a selected_sota_exps
    class DummySelected:
        def __init__(self):
            # hypothesis attribute with nested hypothesis string
            self.hypothesis = types.SimpleNamespace(hypothesis="HYP1")

    class DummyValidationSelector:
        def __init__(self, candidate, direction_sign, competition, only_sample, sample_code_path, sample_rate):
            # emulate hypothesis_loop_id mapping that maps HYP1 to loop '2' (so final check picks Loop_2)
            self.hypothesis_loop_id = {"HYP1": "2"}

        def get_sota_exp_to_submit(self, trace_arg):
            return DummySelected()

    monkeypatch.setattr(submit_mod, "ValidationSelector", DummyValidationSelector)

    # Finally, call evaluate_one_trace with selector_name 'validation' and debug False
    competition_out, hit, sota_exp_stat = evaluate_one_trace(
        selector_name="validation",
        trace=trace,
        debug=False,
        only_sample=False,
        sample_code_path="",
        sota_result={},
        experiment="validation",
        log_path=tmp_path,
        sample_rate=0.8,
    )

    assert competition_out == competition
    # final_score had any_medal True so hit should be True
    assert hit is True
    # final_score had gold_medal True -> expect 'gold'
    assert sota_exp_stat == "gold"
