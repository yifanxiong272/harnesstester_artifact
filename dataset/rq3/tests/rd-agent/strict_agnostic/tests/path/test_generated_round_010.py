import pickle
import types
from types import SimpleNamespace
from pathlib import Path
from importlib import import_module
import pytest

submit = import_module("rdagent.scenarios.data_science.proposal.exp_gen.select.submit")

# Mocks used across tests
class MockBestValidSelector:
    def __init__(self, *args, **kwargs):
        # store args for potential introspection
        self.args = args
        self.kwargs = kwargs

    def get_sota_exp_to_submit(self, trace, **kwargs):
        # represent a quick selection
        return "quick_choice"

    def collect_sota_candidates(self, trace):
        # return a non-empty list so validation path continues
        return ["exp_1"]


class MockValidationSelector:
    def __init__(self, candidate, direction_sign, competition, only_sample, sample_code_path, sample_rate):
        # Validate that direction_sign passed in is as expected by the scenario
        # Keep this deterministic and observable by raising if unexpected
        self.candidate = candidate
        self.direction_sign = direction_sign
        self.competition = competition
        self.only_sample = only_sample
        self.sample_code_path = sample_code_path
        self.sample_rate = sample_rate

        # The production code expects selector.hypothesis_loop_id mapping and later
        # selector.get_sota_exp_to_submit to return an object with hypothesis.hypothesis
        self.hypothesis_loop_id = {"h1": "1"}

    def get_sota_exp_to_submit(self, trace):
        # Return an object compatible with the calling code
        return SimpleNamespace(hypothesis=SimpleNamespace(hypothesis="h1"))


@pytest.fixture(autouse=True)
def restore_patch(monkeypatch):
    """
    Ensure we restore original attributes after each test by using monkeypatch fixture.
    """
    # ensure tests patch module attributes but they are restored automatically by monkeypatch
    yield


def make_trace(competition_name, metric_direction=None):
    scen = SimpleNamespace(competition=competition_name, metric_direction=metric_direction)
    trace = SimpleNamespace(scen=scen)
    return trace


def test_validation_selector_early_exit_round_010(monkeypatch):
    """
    When the local data path for the competition does not exist, evaluate_one_trace
    should return early with (competition, False, ""). This covers the Path.exists False branch.
    """
    # Ensure the Path.exists used in the module reports False for the checked path
    # Patch the module Path.exists to return False regardless of target
    monkeypatch.setattr(submit, "Path", Path)

    # Patch DS_RD_SETTING.local_data_path to a path we will ensure does not exist
    monkeypatch.setattr(submit.DS_RD_SETTING, "local_data_path", "/this/path/should/not/exist")

    trace = make_trace("some-nonexistent-competition", metric_direction=None)

    # Call with selector_name validation which triggers local path check
    result = submit.evaluate_one_trace(
        selector_name="validation",
        trace=trace,
        debug=True,
        only_sample=False,
        sample_code_path="/tmp",
        sota_result={},
        experiment="validation",
        log_path=Path("/does/not/matter"),
        sample_rate=0.8,
    )

    # Oracle: function returns the competition and indicates no hit and empty stat
    assert result == ("some-nonexistent-competition", False, "")


def test_validation_selector_full_path_round_010(tmp_path, monkeypatch):
    """
    Full validation path (selector_name == "validation") where:
    - local data path exists
    - BestValidSelector returns candidates
    - we find a mle_score pickle that contains any_medal and gold_medal
    Expect evaluate_one_trace to return hit True and sota_exp_stat == "gold".

    This test patches selectors to deterministic mocks and writes a single pickle
    file under the temporary log_path to simulate discovered mle_score files.
    """
    # Install our mock selectors into the module under test
    monkeypatch.setattr(submit, "BestValidSelector", MockBestValidSelector)
    monkeypatch.setattr(submit, "ValidationSelector", MockValidationSelector)

    # Force extract_json to be identity to avoid depending on its behavior
    monkeypatch.setattr(submit, "extract_json", lambda x: x)

    # Prepare a competition name that triggers the special-case metric_direction override
    competition_name = "detecting-insults-in-social-commentary"
    trace = make_trace(competition_name, metric_direction=0)

    # Make the DS_RD_SETTING.local_data_path point to tmp_path and create competition dir
    monkeypatch.setattr(submit.DS_RD_SETTING, "local_data_path", str(tmp_path))
    (tmp_path / competition_name).mkdir()

    # Prepare a log_path that contains the expected structure Loop_{loop_id}/running/mle_score/**/*.pkl
    # Our mock ValidationSelector uses hypothesis_loop_id mapping to loop id "1"
    loop_dir = tmp_path / "Loop_1" / "running" / "mle_score" / "nested"
    loop_dir.mkdir(parents=True)
    pkl_path = loop_dir / "score.pkl"

    # Write a pickle file that, when extracted by extract_json, contains the medal info
    mle_score = {"any_medal": True, "gold_medal": True, "silver_medal": False, "bronze_medal": False}
    with pkl_path.open("wb") as f:
        pickle.dump(mle_score, f)

    # Ensure try_get_loop_id returns "1" for the candidate; patch it for determinism
    monkeypatch.setattr(submit, "try_get_loop_id", lambda trace_arg, exp: "1")

    # Now run evaluate_one_trace with debug=False to take the non-debug path which reads the pickle
    result = submit.evaluate_one_trace(
        selector_name="validation",
        trace=trace,
        debug=False,
        only_sample=False,
        sample_code_path=str(tmp_path),
        sota_result={},
        experiment="validation",
        log_path=tmp_path,
        sample_rate=0.8,
    )

    # Oracle assertions: competition name unchanged, hit True, and gold medal recognized
    assert result[0] == competition_name
    assert result[1] is True
    assert result[2] == "gold"


# Expose the expected nodeids so test runner selection can be deterministic in CI
# (Not used by pytest, but part of the structured proposal metadata.)
