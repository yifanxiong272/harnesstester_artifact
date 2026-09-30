import pytest
from types import SimpleNamespace

# Import the real RetryAgent class to exercise the real method under test.
from sweagent.agent.agents import RetryAgent


def test_finalize_agent_run_appends_and_updates_round_082():
    """Verify that _finalize_agent_run calls save_trajectory, appends trajectory data,
    and increments _total_instance_attempt_stats by agent.model.stats.
    """
    # Create an uninitialized RetryAgent instance without invoking __init__.
    ra = object.__new__(RetryAgent)

    # Prepare internal state expected by _finalize_agent_run
    ra._attempt_data = []
    ra._total_instance_attempt_stats = 0

    # Build a fake agent object with the exact attributes & methods the method uses.
    saved = {"called": False}

    def save_trajectory():
        saved["called"] = True

    traj_payload = {"steps": ["a", "b"]}
    fake_model = SimpleNamespace(stats=42)
    fake_agent = SimpleNamespace(
        save_trajectory=save_trajectory,
        get_trajectory_data=lambda: traj_payload,
        model=fake_model,
    )

    ra._agent = fake_agent

    # Execute the method under test
    ra._finalize_agent_run()

    # Oracles: save was called, trajectory appended, and stats added.
    assert saved["called"] is True
    assert ra._attempt_data[-1] is traj_payload  # same object returned appended
    assert ra._total_instance_attempt_stats == 42


def test_finalize_agent_run_asserts_when_no_agent_round_082():
    """Verify that an AssertionError is raised when _agent is None (the assert at line 322).
    """
    ra = object.__new__(RetryAgent)
    # Ensure required attributes exist but _agent is explicitly None to trigger the assert
    ra._attempt_data = []
    ra._total_instance_attempt_stats = 0
    ra._agent = None

    with pytest.raises(AssertionError):
        ra._finalize_agent_run()
