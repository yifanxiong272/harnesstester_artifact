import asyncio
import copy
import pytest

from sweagent.agent.agents import DefaultAgent


class FakeLogger:
    def __init__(self):
        self.warnings = []
        self.errors = []
        self.infos = []

    def warning(self, *args, **kwargs):
        self.warnings.append((args, kwargs))

    def error(self, *args, **kwargs):
        self.errors.append((args, kwargs))

    def info(self, *args, **kwargs):
        self.infos.append((args, kwargs))


class FakeStep:
    def __init__(self, submission=None, exit_status="exit", observation=""):
        # attributes used by attempt_autosubmission_after_error
        self.submission = submission
        self.exit_status = exit_status
        self.observation = observation
        self.done = False

    def model_copy(self, deep=True):
        # return a shallow copy as the method under test calls model_copy(deep=True)
        return copy.copy(self)


class FakeDeployment:
    def __init__(self, alive: bool):
        self._alive = alive

    async def is_alive(self, timeout=0):
        # deterministic, immediate
        await asyncio.sleep(0)
        return self._alive


class FakeRepo:
    def __init__(self, repo_name):
        self.repo_name = repo_name


class FakeEnv:
    def __init__(self, deployment_alive: bool, repo=None, execute_raises=False):
        self.deployment = FakeDeployment(deployment_alive)
        self.repo = repo
        self._execute_called = False
        self._execute_raises = execute_raises

    def execute_command(self, *args, **kwargs):
        self._execute_called = True
        if self._execute_raises:
            raise RuntimeError("execute failed")
        return 0


def make_agent_with_env(env, trajectory=None):
    # create DefaultAgent instance without running __init__ and populate required attributes
    agent = object.__new__(DefaultAgent)
    agent.logger = FakeLogger()
    agent._env = env
    # The DefaultAgent exposes `trajectory` as a property without a setter. Use the underlying
    # backing attribute (commonly _trajectory) to avoid triggering the property setter error.
    backing = [] if trajectory is None else list(trajectory)
    setattr(agent, "_trajectory", backing)

    # handle_submission will be monkeypatched in some tests; provide a default that
    # returns the passed step unchanged
    def default_handle_submission(step, observation="", force_submission=False):
        return step

    agent.handle_submission = default_handle_submission
    return agent


def test_autosubmit_no_trajectory_round_016():
    # If the runtime is dead and there is no previous trajectory, we should return the step unchanged
    env = FakeEnv(deployment_alive=False, repo=None)
    agent = make_agent_with_env(env, trajectory=[])
    step = FakeStep(submission=None, exit_status="failed")

    returned = DefaultAgent.attempt_autosubmission_after_error(agent, step)

    # model_copy sets done=True on the returned step object
    assert returned.done is True
    # nothing was submitted
    assert returned.submission is None
    # we expect that the agent logged an error about runtime not alive and an info about no last trajectory
    assert any("Runtime is no longer alive" in args[0] for args, _ in agent.logger.errors)
    assert any("No last trajectory step to extract patch from" in args[0] for args, _ in agent.logger.infos)


def test_autosubmit_no_diff_in_last_trajectory_round_016():
    # If runtime dead but last trajectory has no diff in state, function should return step unchanged
    last_step = {"state": {}}  # no 'diff' key
    env = FakeEnv(deployment_alive=False, repo=None)
    agent = make_agent_with_env(env, trajectory=[last_step])
    step = FakeStep(submission=None, exit_status="failed")

    returned = DefaultAgent.attempt_autosubmission_after_error(agent, step)

    assert returned.done is True
    assert returned.submission is None
    # confirm log entry indicating no diff
    assert any("No diff in last trajectory step state" in args[0] for args, _ in agent.logger.infos)


def test_autosubmit_with_empty_diff_round_016():
    # If runtime dead and last trajectory has an empty diff, submission becomes empty and triggers the empty-diff branch
    last_step = {"state": {"diff": ""}}
    env = FakeEnv(deployment_alive=False, repo=None)
    agent = make_agent_with_env(env, trajectory=[last_step])
    step = FakeStep(submission=None, exit_status="failed")

    returned = DefaultAgent.attempt_autosubmission_after_error(agent, step)

    # submission is set to empty string
    assert returned.submission == ""
    # because submission is falsey, observation should not be set to the autosubmitted message
    assert returned.observation == ""
    # confirm log entry about empty diff
    assert any("Diff from last traj step empty." in args[0] for args, _ in agent.logger.infos)


def test_autosubmit_with_nonempty_diff_round_016():
    # If runtime dead and last trajectory contains a non-empty diff, the step should be autosubmitted and meta updated
    last_step = {"state": {"diff": "some patch content"}}
    env = FakeEnv(deployment_alive=False, repo=None)
    agent = make_agent_with_env(env, trajectory=[last_step])
    # start with an exit_status to verify it gets wrapped into submitted(...)
    step = FakeStep(submission=None, exit_status="original_exit")

    returned = DefaultAgent.attempt_autosubmission_after_error(agent, step)

    assert returned.submission == "some patch content"
    assert returned.observation == "Environment died unexpectedly. Exited (autosubmitted)"
    assert returned.exit_status == "submitted (original_exit)"


def test_autosubmit_env_alive_and_handle_submission_round_016():
    # If the runtime is alive, we should build a repo path and execute the submission command; then
    # call handle_submission. We monkeypatch handle_submission to force a successful autosubmit.
    class FakeRepo:
        def __init__(self, repo_name):
            self.repo_name = repo_name

    fake_repo = FakeRepo("myrepo")
    env = FakeEnv(deployment_alive=True, repo=fake_repo, execute_raises=False)
    agent = make_agent_with_env(env, trajectory=[])

    # monkeypatch handle_submission to simulate finding a submission upon checking the model.patch file
    def fake_handle_submission(step, observation="", force_submission=False):
        step.submission = "from handle_submission"
        return step

    agent.handle_submission = fake_handle_submission

    step = FakeStep(submission=None, exit_status="abc")

    returned = DefaultAgent.attempt_autosubmission_after_error(agent, step)

    # execute_command should have been invoked
    assert env._execute_called is True
    # handle_submission produced a submission leading to the autosubmit exit branch
    assert returned.submission == "from handle_submission"
    assert returned.observation == "Exited (autosubmitted)"
