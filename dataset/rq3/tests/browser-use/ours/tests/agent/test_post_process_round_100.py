import asyncio
from types import SimpleNamespace
import pytest

from browser_use.agent.service import Agent


class FakeLogger:
    def __init__(self):
        self.debug_messages = []
        self.info_messages = []

    def debug(self, msg):
        # keep deterministic string storage
        self.debug_messages.append(str(msg))

    def info(self, msg):
        self.info_messages.append(str(msg))


class FakeResult:
    def __init__(self, *, error=False, is_done=False, success=False, extracted_content="", attachments=None):
        self.error = error
        self.is_done = is_done
        self.success = success
        self.extracted_content = extracted_content
        self.attachments = attachments or []


class FakeState:
    def __init__(self, *, last_model_output=None, last_result=None, consecutive_failures=0, n_steps=1):
        self.last_model_output = last_model_output
        self.last_result = last_result
        self.consecutive_failures = consecutive_failures
        self.n_steps = n_steps


def make_fake_self(*, browser_session=True, last_model_output=None, last_result=None, consecutive_failures=0):
    """Construct a minimal fake `self` with the attributes and callables used by Agent._post_process.
    The function purposely avoids any I/O and is fully deterministic."""
    fake = SimpleNamespace()
    fake.browser_session = browser_session

    # recorders for calls
    fake._check_and_update_downloads_calls = []

    async def _check_and_update_downloads(context):
        # record call and return immediately
        fake._check_and_update_downloads_calls.append(context)

    fake._check_and_update_downloads = _check_and_update_downloads

    fake._update_plan_from_model_output_calls = []

    def _update_plan_from_model_output(model_output):
        fake._update_plan_from_model_output_calls.append(model_output)

    fake._update_plan_from_model_output = _update_plan_from_model_output

    fake._update_loop_detector_actions_calls = []

    def _update_loop_detector_actions():
        fake._update_loop_detector_actions_calls.append(True)

    fake._update_loop_detector_actions = _update_loop_detector_actions

    fake.logger = FakeLogger()
    fake.state = FakeState(last_model_output=last_model_output, last_result=last_result, consecutive_failures=consecutive_failures)
    return fake


def test_assert_browser_session_round_100():
    """Ensure assertion triggers when browser_session is not set."""
    post = Agent._post_process
    fake = make_fake_self(browser_session=None)

    with pytest.raises(AssertionError) as exc:
        # run coroutine synchronously for determinism
        asyncio.run(post(fake))

    assert 'BrowserSession is not set up' in str(exc.value)


def test_update_plan_and_loop_update_round_100():
    """When last_model_output is present, _update_plan_from_model_output should be invoked and loop detector updated; downloads check awaited."""
    post = Agent._post_process
    model_out = {"plan": "do_stuff"}
    fake = make_fake_self(browser_session=True, last_model_output=model_out, last_result=[])

    # run
    asyncio.run(post(fake))

    # _check_and_update_downloads awaited with expected context
    assert fake._check_and_update_downloads_calls == ["after executing actions"]

    # plan update called with exact object
    assert fake._update_plan_from_model_output_calls == [model_out]

    # loop detector was updated exactly once
    assert len(fake._update_loop_detector_actions_calls) == 1


def test_single_error_increments_and_returns_round_100():
    """If the step produced a single error result, consecutive_failures increments and function returns early (no final info logged)."""
    post = Agent._post_process
    # one result with error True triggers early return
    result = FakeResult(error=True, is_done=False, success=False, extracted_content="", attachments=[])
    fake = make_fake_self(browser_session=True, last_model_output=None, last_result=[result], consecutive_failures=0)

    asyncio.run(post(fake))

    # consecutive failures incremented by 1
    assert fake.state.consecutive_failures == 1

    # logger.debug should have been called with a consecutive failures message
    assert any('Consecutive failures' in msg for msg in fake.logger.debug_messages)

    # no final info logs when returned early
    assert fake.logger.info_messages == []


def test_reset_consecutive_failures_and_log_success_with_attachments_round_100():
    """When last_result exists and is done (success True) and there were consecutive failures, they are reset; info logs include final result and attachments (multiple)."""
    post = Agent._post_process
    # single result, not an error, is_done True and success True with two attachments
    res = FakeResult(error=False, is_done=True, success=True, extracted_content="OK_CONTENT", attachments=["/tmp/a.txt", "/tmp/b.txt"])
    fake = make_fake_self(browser_session=True, last_model_output=None, last_result=[res], consecutive_failures=2)

    asyncio.run(post(fake))

    # consecutive failures reset to 0
    assert fake.state.consecutive_failures == 0

    # logger.info should contain the final result message (green) and two attachment lines
    info_msgs = "\n".join(fake.logger.info_messages)
    assert 'Final Result' in info_msgs
    assert 'OK_CONTENT' in info_msgs
    # attachment lines expected for 2 attachments
    assert 'Attachment 1' in info_msgs
    assert 'Attachment 2' in info_msgs


def test_final_result_failure_branch_single_attachment_round_100():
    """When final result indicates failure, red branch should be logged and single attachment formatting uses the empty index placeholder."""
    post = Agent._post_process
    res = FakeResult(error=False, is_done=True, success=False, extracted_content="BAD", attachments=["/tmp/only.txt"])
    fake = make_fake_self(browser_session=True, last_model_output=None, last_result=[res], consecutive_failures=0)

    asyncio.run(post(fake))

    info_msgs = "\n".join(fake.logger.info_messages)
    # ensures failure branch message logged and contains the content
    assert 'Final Result' in info_msgs
    assert 'BAD' in info_msgs
    # single attachment formatting should include the file path
    assert ': /tmp/only.txt' in info_msgs
