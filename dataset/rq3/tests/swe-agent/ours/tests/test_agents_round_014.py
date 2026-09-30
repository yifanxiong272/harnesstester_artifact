import asyncio
import copy
import types

import pytest

from sweagent.agent import agents


class DummyStep:
    """A minimal stand-in for StepOutput used by the tested function.

    It implements model_copy(deep=True) which the agent calls and exposes
    the attributes the function reads/writes: done, submission, observation,
    exit_status.
    """

    def __init__(self, done=False, submission=None, observation=None, exit_status=None):
        self.done = done
        self.submission = submission
        self.observation = observation
        self.exit_status = exit_status

    def model_copy(self, deep: bool = False):
        # Return a deep copy so mutations don't affect the original passed in test object
        return copy.deepcopy(self)


class SimpleDeployment:
    def __init__(self, alive_return: bool):
        # is_alive must be an async function because the production code calls
        # asyncio.run(self._env.deployment.is_alive(...))
        async def _is_alive(timeout=0):
            return alive_return

        self.is_alive = _is_alive


class SimpleRepo:
    def __init__(self, repo_name: str):
        self.repo_name = repo_name


class SimpleEnv:
    def __init__(self, deployment_alive: bool, repo=None):
        self.deployment = SimpleDeployment(deployment_alive)
        # execute_command should be callable; tests will replace or inspect it
        self.execute_command_called = None
        self.execute_command = lambda *a, **k: None
        self.repo = repo


def make_agent_with_env(env, trajectory=None):
    # Create a DefaultAgent instance without invoking its heavy constructor.
    agent = object.__new__(agents.DefaultAgent)
    # Provide minimal attributes used by attempt_autosubmission_after_error
    agent.logger = agents.get_logger("test-agent")
    agent._env = env
    # DefaultAgent.trajectory is a read-only property; set the underlying storage.
    # The DefaultAgent implementation uses a private list attribute (commonly _trajectory).
    # Populate that private attribute directly so the trajectory property returns it.
    agent.__dict__["_trajectory"] = trajectory if trajectory is not None else []
    return agent


def test_attempt_autosubmit_dead_no_trajectory_round_014():
    """When the runtime is dead and there is no trajectory, the function should
    return the copied step with done=True and leave submission None.
    """
    env = SimpleEnv(deployment_alive=False, repo=None)
    agent = make_agent_with_env(env, trajectory=[])

    original_step = DummyStep(done=False, submission=None, observation=None, exit_status="err")

    returned = agent.attempt_autosubmission_after_error(original_step)

    # The function should call model_copy and set done True on the returned step
    assert returned is not original_step
    assert returned.done is True
    # Because no trajectory exists, submission remains None and observation unchanged
    assert returned.submission is None
    assert returned.observation is None
    # exit_status should be unchanged because no autosubmission occurred
    assert returned.exit_status == "err"


def test_attempt_autosubmit_dead_with_diff_populated_round_014():
    """When runtime dead but last trajectory step contains a non-empty diff,
    that diff should be applied to submission and observation/exit_status updated.
    """
    diff_text = "--- a/file\n+++ b/file\n@@ -1 +1 @@\n-old\n+new\n"
    last_step = {"state": {"diff": diff_text}}

    env = SimpleEnv(deployment_alive=False, repo=None)
    # Provide a trajectory where the last element contains the diff
    agent = make_agent_with_env(env, trajectory=[{"state": {}}, last_step])

    original_step = DummyStep(done=False, submission=None, observation=None, exit_status="error-code")

    returned = agent.attempt_autosubmission_after_error(original_step)

    # Should have used diff from last trajectory step
    assert returned.submission == diff_text
    assert returned.observation == "Environment died unexpectedly. Exited (autosubmitted)"
    # exit_status should reflect the previous value wrapped with 'submitted (...)'
    assert returned.exit_status == f"submitted ({original_step.exit_status})"


def test_attempt_autosubmit_dead_with_diff_empty_round_014():
    """When runtime dead and last trajectory step contains an empty diff,
    submission should be set (empty) and code should follow the empty-diff branch.
    """
    last_step = {"state": {"diff": ""}}  # explicit empty diff

    env = SimpleEnv(deployment_alive=False, repo=None)
    agent = make_agent_with_env(env, trajectory=[last_step])

    original_step = DummyStep(done=False, submission=None, observation=None, exit_status="E")

    returned = agent.attempt_autosubmission_after_error(original_step)

    # submission set to empty string
    assert returned.submission == ""
    # Because submission is falsy, observation should remain None and exit_status unchanged
    assert returned.observation is None
    assert returned.exit_status == "E"


def test_attempt_autosubmit_env_alive_executes_command_and_handles_submission_round_014():
    """When the environment is alive, the agent should attempt to run the
    submission command and then call handle_submission. If handle_submission
    returns a step with a truthy submission, final observation is set.
    Also assert the repo name is included in cwd when repo is present.
    """
    # Prepare env with deployment alive and a repo present to hit the repo-name branch
    repo = SimpleRepo(repo_name="myrepo")
    env = SimpleEnv(deployment_alive=True, repo=repo)

    executed = {}

    def fake_execute_command(cmd, check=True, cwd=None):
        # record what was executed for assertions
        executed['cmd'] = cmd
        executed['check'] = check
        executed['cwd'] = cwd

    env.execute_command = fake_execute_command

    agent = make_agent_with_env(env, trajectory=[])

    # Patch the agent's handle_submission to return a step with submission set
    def fake_handle_submission(step, observation="", force_submission=False):
        # Simulate that a patch file was found and submission performed
        step.submission = "some-patch"
        return step

    # Bind fake_handle_submission to our agent instance
    agent.handle_submission = types.MethodType(lambda self, step, observation="", force_submission=False: fake_handle_submission(step, observation, force_submission), agent)

    original_step = DummyStep(done=False, submission=None, observation=None, exit_status=None)

    returned = agent.attempt_autosubmission_after_error(original_step)

    # execute_command must have been called with the expected submission command
    assert executed['cmd'] == "git add -A && git diff --cached > /root/model.patch"
    # cwd should include the repo name prefixed with '/'
    assert executed['cwd'] == "/myrepo"

    # Because our fake_handle_submission set submission to non-empty, final observation is set
    assert returned.submission == "some-patch"
    assert returned.observation == "Exited (autosubmitted)"
