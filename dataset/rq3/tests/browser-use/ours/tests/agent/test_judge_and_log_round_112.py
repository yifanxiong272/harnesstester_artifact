import asyncio
from types import SimpleNamespace

from browser_use.agent import service


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []

    def info(self, msg):
        self.infos.append(msg)

    def warning(self, msg):
        self.warnings.append(msg)


class FakeJudgement:
    def __init__(self, verdict, failure_reason=None, reached_captcha=False, reasoning=""):
        self.verdict = verdict
        self.failure_reason = failure_reason
        self.reached_captcha = reached_captcha
        self.reasoning = reasoning


class DummyLastResult:
    def __init__(self, is_done: bool, success: bool):
        self.is_done = is_done
        self.success = success
        # judgement will be attached by _judge_and_log when is_done is True
        self.judgement = None


class DummyHistoryItem:
    def __init__(self, last_result: DummyLastResult):
        self.result = [last_result]


class DummyHistory:
    def __init__(self, item: DummyHistoryItem):
        # mimic the .history attribute used by _judge_and_log
        self.history = [item]


def run_coro(coro):
    # helper to run the async coroutine deterministically
    return asyncio.run(coro)


def make_fake_self(last_result, judgement_return):
    """Construct a fake 'self' object with history, a mocked _judge_trace, and logger.

    judgement_return may be an instance (truthy) or None/False (falsy) to exercise branches.
    """

    async def _judge_trace():
        return judgement_return

    fake = SimpleNamespace()
    fake.history = DummyHistory(DummyHistoryItem(last_result))
    fake._judge_trace = _judge_trace
    fake.logger = DummyLogger()
    return fake


def test_judge_and_log_skips_attach_when_last_not_done_round_112():
    # last_result.is_done is False -> judgement is awaited but should NOT be attached nor logged
    last = DummyLastResult(is_done=False, success=True)
    judgement = FakeJudgement(verdict=True, reasoning="irrelevant")
    fake = make_fake_self(last, judgement)

    # Call the unbound async method with the fake self
    run_coro(service.Agent._judge_and_log(fake))

    # Since is_done was False, judgement must NOT be attached
    assert last.judgement is None
    # No logging should have occurred
    assert fake.logger.infos == []
    assert fake.logger.warnings == []


def test_judge_and_log_early_returns_when_both_report_success_round_112():
    # When agent reports success and judge verdict is True, function should return early and not log
    last = DummyLastResult(is_done=True, success=True)
    judgement = FakeJudgement(verdict=True, reasoning="ok")
    fake = make_fake_self(last, judgement)

    # Execute
    result = run_coro(service.Agent._judge_and_log(fake))

    # last_result.judgement must be attached
    assert last.judgement is judgement
    # early return - no logging
    assert fake.logger.infos == []
    assert fake.logger.warnings == []
    # function should return None explicitly / implicitly
    assert result is None


def test_judge_and_log_warns_on_agent_success_but_judge_fail_round_112():
    # Agent reported success True but judge verdict False -> warning + info must be logged
    last = DummyLastResult(is_done=True, success=True)
    judgement = FakeJudgement(
        verdict=False,
        failure_reason="Could not find element",
        reached_captcha=True,
        reasoning="Detailed reasoning text"
    )
    fake = make_fake_self(last, judgement)

    run_coro(service.Agent._judge_and_log(fake))

    # judgement should be attached to result
    assert last.judgement is judgement

    # Expect a captcha warning recorded via logger.warning
    assert any("captcha" in w.lower() or "blocked by a captcha" in w for w in fake.logger.warnings)

    # Expect info log that includes the FAIL verdict and the reasoning text
    assert any("FAIL" in info or "FAIL" in info for info in fake.logger.infos)
    assert any("Detailed reasoning text" in info for info in fake.logger.infos)


def test_judge_and_log_logs_pass_when_judge_passes_but_agent_failed_round_112():
    # Agent reported failure (False) but judge verdict True -> info with PASS should be logged
    last = DummyLastResult(is_done=True, success=False)
    judgement = FakeJudgement(verdict=True, failure_reason=None, reached_captcha=False, reasoning="All good")
    fake = make_fake_self(last, judgement)

    run_coro(service.Agent._judge_and_log(fake))

    # judgement attached
    assert last.judgement is judgement

    # No captcha warning expected
    assert fake.logger.warnings == []

    # Info should include PASS string
    assert any("PASS" in info for info in fake.logger.infos)
    # It should also include the reasoning we provided
    assert any("All good" in info for info in fake.logger.infos)
