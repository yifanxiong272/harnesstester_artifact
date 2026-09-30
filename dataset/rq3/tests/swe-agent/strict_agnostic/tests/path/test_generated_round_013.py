import copy
from sweagent.agent.reviewer import TrajectoryFormatter


class DummyConfig:
    def __init__(self, *, filter=None, output_filter=None, only_show_last_n_output=0, item_template="{{ i_step }}:{{ action }} -> {{ observation }} (traj {{ i_traj }})"):
        # Using lists to emulate the real config's attributes
        self.filter = list(filter) if filter is not None else []
        self.output_filter = list(output_filter) if output_filter is not None else []
        self.only_show_last_n_output = only_show_last_n_output
        self.item_template = item_template


def test_format_trajectory_filters_and_template_round_013():
    # config filters out actions that start with "skip" and omits outputs that start with "filter_out"
    config = DummyConfig(filter=["skip"], output_filter=["filter_out"], only_show_last_n_output=0)
    fmt = TrajectoryFormatter(config)

    # Prepare trajectory: first item should be excluded by filter; last item should have its output omitted
    step0 = {"action": "  skip this", "observation": "obs0"}  # leading spaces to exercise strip()
    step1 = {"action": "do this", "observation": "obs1"}
    step2 = {"action": "filter_out something", "observation": "obs2"}

    trajectory = [step0, step1, step2]

    formatted = fmt.format_trajectory(trajectory, i_traj=1)

    # Expected: step0 excluded; step1 shows original observation; step2 observation replaced with marker
    expected_step1 = "0:do this -> obs1 (traj 1)"
    expected_step2 = "1:filter_out something -> [Output omitted] (traj 1)"
    expected = expected_step1 + "\n\n" + expected_step2

    assert formatted == expected

    # Ensure original input objects were not mutated by formatting (deepcopy used internally)
    assert step0["observation"] == "obs0"
    assert step2["observation"] == "obs2"


def test_format_trajectory_only_show_last_n_output_round_013():
    # config to only show last 1 output; no action-based output_filter
    config = DummyConfig(filter=[], output_filter=[], only_show_last_n_output=1)
    fmt = TrajectoryFormatter(config)

    # Three steps: first two should have observations omitted, last one preserved
    s0 = {"action": "act0", "observation": "obs0"}
    s1 = {"action": "act1", "observation": "obs1"}
    s2 = {"action": "act2", "observation": "obs2"}

    trajectory = [s0, s1, s2]

    formatted = fmt.format_trajectory(trajectory, i_traj=1)

    expected = (
        "0:act0 -> [Output omitted] (traj 1)\n\n"
        "1:act1 -> [Output omitted] (traj 1)\n\n"
        "2:act2 -> obs2 (traj 1)"
    )

    assert formatted == expected

    # Again ensure original inputs were not mutated
    assert s0["observation"] == "obs0"
    assert s1["observation"] == "obs1"
    assert s2["observation"] == "obs2"
