from sweagent.agent.action_sampler import BinaryTrajectoryComparison


def test_format_trajectory_nonempty_round_065():
    # two-step trajectory: ensures loop body executes and ordering/indexing are correct
    trajectory = [
        {"action": "do X", "observation": "ok"},
        {"action": "do Y", "observation": "fail"},
    ]

    formatted = BinaryTrajectoryComparison._format_trajectory(None, trajectory)

    expected_step0 = "Action 0: do X\n Observation 0: ok"
    expected_step1 = "Action 1: do Y\n Observation 1: fail"
    # The implementation joins step strings with a single newline between them
    expected = expected_step0 + "\n" + expected_step1

    assert formatted == expected


def test_format_trajectory_empty_round_065():
    # empty trajectory: ensures branch where loop does not execute and empty string returned
    trajectory = []

    formatted = BinaryTrajectoryComparison._format_trajectory(None, trajectory)

    assert formatted == ""
