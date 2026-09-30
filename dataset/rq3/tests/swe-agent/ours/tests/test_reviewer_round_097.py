import pytest

from sweagent.agent import reviewer


class DummyRetry(reviewer.AbstractRetryLoop):
    """Concrete implementation to allow instantiation of the abstract base.

    Implements the abstract get_best method deterministically so tests
    remain deterministic.
    """

    def get_best(self) -> int:
        return 42


def test_default_abstract_retry_methods_round_097():
    # Instantiate the concrete subclass
    dr = DummyRetry()

    # retry() should return the default False (covers line 98)
    assert dr.retry() is False

    # get_forwarded_vars() returns an empty dict (covers line 122)
    assert isinstance(dr.get_forwarded_vars(), dict)
    assert dr.get_forwarded_vars() == {}

    # on_attempt_started is a no-op and should return None (covers line 110)
    result = dr.on_attempt_started(0, agent={"some": "agent"})
    assert result is None

    # on_submit and on_model_query accept arguments and do not raise
    # (they have no implementation in the base class)
    dr.on_submit(submission=object())
    dr.on_model_query(attempt_stats=object())

    # ensure our concrete get_best is callable and deterministic
    assert dr.get_best() == 42
