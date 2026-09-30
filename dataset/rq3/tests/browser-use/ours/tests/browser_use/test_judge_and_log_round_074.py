import asyncio
from types import SimpleNamespace

import browser_use.beta.service as service


class _LoggerCapture:
    def __init__(self):
        self.infos = []
        self.warnings = []

    def info(self, msg):
        # emulate logger.info signature
        self.infos.append(msg)

    def warning(self, msg):
        # emulate logger.warning signature
        self.warnings.append(msg)


class _Result:
    def __init__(self, is_done, success, judgement=None):
        self.is_done = is_done
        self.success = success
        self.judgement = judgement
        # fields that _judge_and_log reads/sets
        self.reasoning = None
        self.failure_reason = None
        self.reached_captcha = False


class _Step:
    def __init__(self, results):
        # results is a list (the code uses last_step.result[-1])
        self.result = results


class _Judgement:
    def __init__(self, verdict=None, failure_reason=None, reached_captcha=False, reasoning=""):
        self.verdict = verdict
        self.failure_reason = failure_reason
        self.reached_captcha = reached_captcha
        self.reasoning = reasoning


class _FakeSelf:
    def __init__(self, judgement_return, history_list):
        # history_list should be a list of _Step
        self.history = SimpleNamespace(history=history_list)
        self._judgement_to_return = judgement_return
        self.logger = _LoggerCapture()

    async def _judge_trace(self):
        # emulate async behaviour deterministically
        return self._judgement_to_return


def _run_coro(coro):
    # Use asyncio.run deterministically to avoid 'no current event loop' errors.
    return asyncio.run(coro)


def test_no_history_returns_without_logging_round_074():
    # history empty -> early return without logging
    fake = _FakeSelf(judgement_return=_Judgement(verdict=True, reasoning="ok"), history_list=[])
    _run_coro(service.Agent._judge_and_log(fake))

    assert fake.logger.infos == []
    assert fake.logger.warnings == []


def test_last_step_no_result_returns_without_logging_round_074():
    # last_step.result is empty -> early return
    step = _Step(results=[])
    fake = _FakeSelf(judgement_return=_Judgement(verdict=True, reasoning="ok"), history_list=[step])
    _run_coro(service.Agent._judge_and_log(fake))

    assert fake.logger.infos == []
    assert fake.logger.warnings == []


def test_last_result_not_done_returns_without_logging_round_074():
    # last_result.is_done False -> early return
    r = _Result(is_done=False, success=False)
    step = _Step(results=[r])
    fake = _FakeSelf(judgement_return=_Judgement(verdict=True, reasoning="ok"), history_list=[step])
    _run_coro(service.Agent._judge_and_log(fake))

    # judgement should not be attached and no logs
    assert r.judgement is None
    assert fake.logger.infos == []
    assert fake.logger.warnings == []


def test_no_judgement_attached_and_returns_round_074():
    # judge returns falsy (None) -> last_result.judgement set to None then return
    r = _Result(is_done=True, success=False, judgement="initial")
    r.reasoning = "orig"
    step = _Step(results=[r])
    fake = _FakeSelf(judgement_return=None, history_list=[step])

    _run_coro(service.Agent._judge_and_log(fake))

    # the method assigns last_result.judgement = None then returns (no logs)
    assert r.judgement is None
    assert fake.logger.infos == []
    assert fake.logger.warnings == []


def test_success_reported_and_judge_verdict_true_returns_without_logging_round_074():
    # if agent reported success True and judge verdict True -> early return after attaching judgement
    r = _Result(is_done=True, success=True)
    step = _Step(results=[r])
    judge = _Judgement(verdict=True, reasoning="nice")
    fake = _FakeSelf(judgement_return=judge, history_list=[step])

    _run_coro(service.Agent._judge_and_log(fake))

    # judgement attached but no logs since both report success
    assert r.judgement is judge
    assert fake.logger.infos == []
    assert fake.logger.warnings == []


def test_agent_reported_success_but_judge_failed_emits_warning_and_info_round_074():
    # covers branch where self_reported_success True and judgement.verdict False
    r = _Result(is_done=True, success=True)
    step = _Step(results=[r])
    judge = _Judgement(verdict=False, failure_reason="element missing", reached_captcha=True, reasoning="Clicked wrong button")
    fake = _FakeSelf(judgement_return=judge, history_list=[step])

    _run_coro(service.Agent._judge_and_log(fake))

    # judgement attached
    assert r.judgement is judge

    # warning should include the captcha nudge text when reached_captcha True
    assert any('captcha' in w.lower() or 'blocked by a captcha' in w.lower() for w in fake.logger.warnings), \
        f"Expected captcha warning in warnings, got: {fake.logger.warnings}"

    # info should contain the judge verdict and failure_reason and reasoning
    assert fake.logger.infos, "Expected at least one info log"
    info_msg = fake.logger.infos[-1]
    assert 'Judge Verdict' in info_msg
    assert 'FAIL' in info_msg or '\u274c' in info_msg
    assert 'element missing' in info_msg
    assert 'Clicked wrong button' in info_msg
