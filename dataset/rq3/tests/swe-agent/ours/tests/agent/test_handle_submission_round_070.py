import pytest
from types import SimpleNamespace
from sweagent.agent.agents import DefaultAgent


class FakeStep:
    def __init__(self, observation="", submission=None, exit_status=None, done=False, copy_marker=None):
        self.observation = observation
        self.submission = submission
        self.exit_status = exit_status
        self.done = done
        # marker to detect model_copy was called
        self._copy_marker = copy_marker

    def model_copy(self, deep=True):
        # return a distinct object to emulate pydantic model_copy
        return FakeStep(
            observation=self.observation,
            submission=self.submission,
            exit_status=self.exit_status,
            done=self.done,
            copy_marker="copied",
        )


class FakeLogger:
    def __init__(self):
        self.warnings = []
        self.exceptions = []
        self.infos = []

    def warning(self, msg, *args, **kwargs):
        # record the literal message as called
        self.warnings.append((msg, args))

    def exception(self, msg, *args, **kwargs):
        # logger.exception is called with format string and exception object
        self.exceptions.append((msg, args))

    def info(self, msg, *args, **kwargs):
        self.infos.append((msg, args))


class FakeTools:
    def __init__(self, should_signal_submission: bool):
        self._should = should_signal_submission

    def check_for_submission_cmd(self, observation: str) -> bool:
        # intentionally deterministic
        return self._should


class FakeEnvRaise:
    def __init__(self, exc):
        self._exc = exc

    def read_file(self, path, encoding=None, errors=None):
        raise self._exc


class FakeEnvReturn:
    def __init__(self, content: str):
        self._content = content

    def read_file(self, path, encoding=None, errors=None):
        return self._content


class FakeSelf:
    def __init__(self, tools, env, logger=None):
        self.tools = tools
        self._env = env
        self.logger = logger or FakeLogger()


def test_handle_submission_file_not_found_round_070():
    """When env.read_file raises FileNotFoundError, the method should log a warning and
    return the copied step object unchanged (early return).
    """
    original = FakeStep(observation="some observation")
    tools = FakeTools(should_signal_submission=True)
    logger = FakeLogger()
    env = FakeEnvRaise(FileNotFoundError())
    selfobj = FakeSelf(tools=tools, env=env, logger=logger)

    result = DefaultAgent.handle_submission(selfobj, original, observation="")

    # The function calls model_copy first and returns that copy on FileNotFoundError
    assert isinstance(result, FakeStep)
    assert result is not original
    assert getattr(result, "_copy_marker") == "copied"

    # logger.warning should have been called with the expected message
    assert any(wn[0] == "Submission file not found, no submission was made" for wn in logger.warnings)


def test_handle_submission_read_error_round_070():
    """When env.read_file raises a non-FileNotFoundError exception, logger.exception is invoked
    and the copied step is returned.
    """
    original = FakeStep(observation="obs")
    tools = FakeTools(should_signal_submission=True)
    logger = FakeLogger()
    # raise a ValueError to exercise the generic Exception branch
    err = ValueError("boom")
    env = FakeEnvRaise(err)
    selfobj = FakeSelf(tools=tools, env=env, logger=logger)

    result = DefaultAgent.handle_submission(selfobj, original, observation=None)

    assert isinstance(result, FakeStep)
    assert result is not original
    assert result._copy_marker == "copied"

    # Check that logger.exception was called with the expected format string and exception
    assert any(exc[0] == "Failed to read submission file, got %s" and exc[1] and exc[1][0] is err for exc in logger.exceptions)


def test_handle_submission_with_existing_exit_status_round_070():
    """When a non-empty submission is read and the step already has an exit_status,
    the exit_status should be wrapped as 'submitted (previous)'. Also, submission, observation,
    done flag and logger.info should be set appropriately.
    """
    original = FakeStep(observation="orig obs", submission=None, exit_status="previous", done=False)
    tools = FakeTools(should_signal_submission=True)
    logger = FakeLogger()
    content = "patch content\n"
    env = FakeEnvReturn(content)
    selfobj = FakeSelf(tools=tools, env=env, logger=logger)

    result = DefaultAgent.handle_submission(selfobj, original, observation="")

    # Because model_copy is performed, we expect a copy
    assert isinstance(result, FakeStep)
    assert result is not original
    assert result._copy_marker == "copied"

    # submission should be the raw returned content and observation set to same
    assert result.submission == content
    assert result.observation == content

    # since there was a prior exit_status and submission is non-empty, we hit the branch that
    # formats the exit_status as 'submitted (previous)'
    assert result.exit_status == "submitted (previous)"

    # done must be set True and logger.info should have a message about the found submission
    assert result.done is True
    assert any(msg[0].startswith("Found submission:") for msg in logger.infos)
