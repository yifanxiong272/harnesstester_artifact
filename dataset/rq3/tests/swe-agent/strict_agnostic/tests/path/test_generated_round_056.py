import types
import builtins
from types import SimpleNamespace
import sweagent.agent.models as models


class _CaptureLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, msg):
        # store exact message for assertions
        self.warnings.append(str(msg))


class _Outcome:
    def __init__(self, exc):
        self._exc = exc

    def exception(self):
        return self._exc


class _Attempt:
    def __init__(self, retry_state):
        self.retry_state = retry_state

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # do not suppress exceptions
        return False


class DummyRetrying:
    """A minimal replacement for tenacity.Retrying used in tests.

    Behavior:
    - Iteration yields two attempt objects (module-level attributes set by the test):
      models._TEST_ATTEMPT1 then models._TEST_ATTEMPT2.
    - Before yielding the second attempt, calls the provided before_sleep callback
      (if any) to simulate the tenacity before-sleep hook. This invocation happens
      while the caller's 'attempt' name is still bound to the first yielded
      attempt, which matches how the real before_sleep sees the previous attempt.
    """

    def __init__(self, *args, before_sleep=None, **kwargs):
        self.before_sleep = before_sleep
        self._i = 0

    def __iter__(self):
        self._i = 0
        return self

    def __next__(self):
        if self._i == 0:
            self._i += 1
            return getattr(models, "_TEST_ATTEMPT1")
        elif self._i == 1:
            # simulate tenacity calling before_sleep between attempts
            if self.before_sleep:
                # pass a minimal dummy RetryCallState; the implementation under
                # test does not use this parameter for lookup, so None is fine.
                try:
                    self.before_sleep(None)
                except Exception:
                    # Ensure any unexpected exceptions from calling the callback
                    # propagate so tests fail noisily.
                    raise
            self._i += 1
            return getattr(models, "_TEST_ATTEMPT2")
        else:
            raise StopIteration


def _make_instance(return_values):
    """Create a LiteLLMModel-like instance without invoking its real __init__.

    The returned object has the attributes that LiteLLMModel.query expects:
    - logger with a .warning method (captured)
    - config with a retry namespace
    - _query callable
    - _history_to_messages callable
    """
    inst = object.__new__(models.LiteLLMModel)
    inst.logger = _CaptureLogger()
    inst.config = SimpleNamespace(retry=SimpleNamespace(retries=3, min_wait=0, max_wait=0))

    # deterministic _history_to_messages
    inst._history_to_messages = lambda history: ["msg1"]

    # _query returns a shallow copy of return_values so tests can mutate safely
    def _q(messages, n=None, temperature=None):
        # emulate original API returning list
        return list(return_values)

    inst._query = _q
    return inst


def test_retry_warning_no_exception_and_n_default_round_056():
    """Cover branch where previous attempt has no outcome.exception() and default n==1.

    Expected observable behaviors:
    - logger.warning is called and its message does NOT contain the substring 'due to '
      because the previous attempt's outcome.exception() is None.
    - query returns the single element (result[0]) when n is None or 1.
    """
    # Prepare two attempts: first with no outcome, second (not used for message) arbitrary
    attempt1_state = SimpleNamespace(
        outcome=None,
        attempt_number=1,
        idle_for=0.0,
    )
    attempt2_state = SimpleNamespace(
        outcome=None,
        attempt_number=2,
        idle_for=0.0,
    )

    models._TEST_ATTEMPT1 = _Attempt(attempt1_state)
    models._TEST_ATTEMPT2 = _Attempt(attempt2_state)

    # Patch the module Retrying to our DummyRetrying
    original_retrying = models.Retrying
    models.Retrying = DummyRetrying

    try:
        inst = _make_instance([{"text": "ok"}])

        # call query with default n (None -> treated as 1 in behavior) so it returns single dict
        result = models.LiteLLMModel.query(inst, history=None, n=None, temperature=None)

        # returned should be first element of list
        assert isinstance(result, dict)
        assert result == {"text": "ok"}

        # logger should have recorded a warning message when the retry hook was invoked
        # the message should not contain 'due to' because outcome was None
        warnings = inst.logger.warnings
        # ensure at least one warning was recorded
        assert len(warnings) >= 1
        found = False
        for w in warnings:
            if "Retrying LM query" in w:
                found = True
                assert "due to" not in w
        assert found, f"expected a retry warning message, got: {warnings}"
    finally:
        # restore
        models.Retrying = original_retrying
        # cleanup test attributes
        for k in ("_TEST_ATTEMPT1", "_TEST_ATTEMPT2"):
            if hasattr(models, k):
                delattr(models, k)


def test_retry_warning_with_exception_and_n_gt1_round_056():
    """Cover branch where previous attempt had an exception and n>1.

    Expected observable behaviors:
    - logger.warning is called and its message contains 'due to <ExceptionClassName>:'
      because the previous attempt's outcome.exception() returns an Exception instance.
    - when n > 1, query returns the entire list (not just the first element).
    """
    # previous attempt outcome.exception returns an exception instance
    exc_instance = ValueError("bad stuff")
    outcome_with_exc = _Outcome(exc_instance)

    attempt1_state = SimpleNamespace(
        outcome=outcome_with_exc,
        attempt_number=3,
        idle_for=1.234,
    )
    attempt2_state = SimpleNamespace(
        outcome=None,
        attempt_number=4,
        idle_for=0.0,
    )

    models._TEST_ATTEMPT1 = _Attempt(attempt1_state)
    models._TEST_ATTEMPT2 = _Attempt(attempt2_state)

    # Patch Retrying
    original_retrying = models.Retrying
    models.Retrying = DummyRetrying

    try:
        # Prepare instance whose _query returns two items
        inst = _make_instance([{"text": "one"}, {"text": "two"}])

        # call query with n=2 to get whole list
        result = models.LiteLLMModel.query(inst, history=None, n=2, temperature=None)

        # result should be the entire list of two dicts
        assert isinstance(result, list)
        assert result == [{"text": "one"}, {"text": "two"}]

        # logger should have recorded a warning including the exception class name
        warnings = inst.logger.warnings
        assert len(warnings) >= 1
        found = False
        for w in warnings:
            if "Retrying LM query" in w:
                found = True
                # should mention exception class and message
                assert "due to ValueError" in w
                assert "bad stuff" in w
        assert found, f"expected a retry warning message with exception info, got: {warnings}"
    finally:
        models.Retrying = original_retrying
        for k in ("_TEST_ATTEMPT1", "_TEST_ATTEMPT2"):
            if hasattr(models, k):
                delattr(models, k)
