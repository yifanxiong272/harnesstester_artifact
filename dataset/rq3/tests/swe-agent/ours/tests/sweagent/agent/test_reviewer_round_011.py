import copy
from types import SimpleNamespace

from sweagent.agent.reviewer import TrajectoryFormatter


def test_include_and_format_step_exclusion_round_011():
    # Config filters out actions that start with "skip"
    cfg = SimpleNamespace(
        filter=["skip"],
        only_show_last_n_output=0,
        output_filter=[],
        item_template="{{ i_step }}: {{ action }} -> {{ observation }}",
    )

    fmt = TrajectoryFormatter(cfg)

    # First step should be excluded (starts with "skip"), second included
    traj = [
        {"action": "skip me", "observation": "obs_skip"},
        {"action": " do it ", "observation": "obs_do"},
    ]

    out = fmt.format_trajectory(traj, i_traj=1)

    # Only the second (included) step should be present; note action preserved (including surrounding spaces)
    assert "skip me" not in out
    assert out == "0:  do it  -> obs_do"


def test_output_omitted_by_only_show_last_n_round_011():
    # only_show_last_n_output = 1 means all but the last 1 outputs are omitted
    cfg = SimpleNamespace(
        filter=[],
        only_show_last_n_output=1,
        output_filter=[],
        item_template="{{ i_step }}: {{ action }} -> {{ observation }}",
    )

    fmt = TrajectoryFormatter(cfg)

    # Two steps: first's output should be omitted, second shown
    step0 = {"action": "a", "observation": "obs1"}
    step1 = {"action": "b", "observation": "obs2"}

    # Keep originals to assert they are not mutated by formatting
    original0 = copy.deepcopy(step0)
    original1 = copy.deepcopy(step1)

    traj = [step0, step1]
    out = fmt.format_trajectory(traj)

    # Rendered output should show omission for the first step and real observation for the last
    expected = "0: a -> [Output omitted]\n\n1: b -> obs2"
    assert out == expected

    # The original step dictionaries must not be mutated by format_trajectory
    assert step0 == original0
    assert step1 == original1


def test_output_excluded_by_output_filter_round_011():
    # output_filter excludes steps whose action starts with any of its entries
    cfg = SimpleNamespace(
        filter=[],
        only_show_last_n_output=0,
        output_filter=["secret"],
        item_template="{{ i_step }}: {{ action }} -> {{ observation }}",
    )

    fmt = TrajectoryFormatter(cfg)

    # A single step with action starting with "secret" should have its observation omitted
    step = {"action": "secret_action", "observation": "top_secret"}
    original = copy.deepcopy(step)
    out = fmt.format_trajectory([step])

    assert out == "0: secret_action -> [Output omitted]"

    # Ensure the original dict was not mutated
    assert step == original
