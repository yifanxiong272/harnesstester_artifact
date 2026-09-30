import types
from types import SimpleNamespace

import pytest

from sweagent.agent import reviewer
from sweagent.agent.reviewer import ChooserRetryLoop


class DummyLogger:
    def __init__(self):
        self.infos = []

    def info(self, msg):
        # record messages for assertions
        self.infos.append(str(msg))


class FakeStats:
    def __init__(self, instance_cost: float):
        self.instance_cost = instance_cost


class DummyChooser:
    def __init__(self, cfg=None):
        # accept any config and do nothing
        self.cfg = cfg


def _set_class_property(cls, name, value):
    """Replace a class attribute with a simple property returning value.
    Returns the original attribute for later restoration.
    """
    orig = getattr(cls, name, None)
    prop = property(lambda self, _v=value: _v)
    setattr(cls, name, prop)
    return orig


def _restore_class_attr(cls, name, orig):
    if orig is None:
        try:
            delattr(cls, name)
        except Exception:
            pass
    else:
        setattr(cls, name, orig)


def _patch_module_chooser(dummy):
    orig = getattr(reviewer, "Chooser", None)
    reviewer.Chooser = dummy
    return orig


def _restore_module_chooser(orig):
    if orig is None:
        try:
            delattr(reviewer, "Chooser")
        except Exception:
            pass
    else:
        reviewer.Chooser = orig


def test_retry_returns_false_when_total_cost_exceeds_limit_round_026():
    """Covers branch: self._total_stats.instance_cost > self._config.cost_limit > 0 -> False
    """
    # prepare config so cost_limit > 0 and include chooser attr to satisfy __init__
    cfg = SimpleNamespace(cost_limit=10, max_attempts=5, min_budget_for_new_attempt=0, chooser=SimpleNamespace())

    # patch module Chooser to a dummy so __init__ doesn't require a complex config
    orig_module_chooser = _patch_module_chooser(DummyChooser)

    # patch class properties to control values used inside retry()
    orig_stats = _set_class_property(ChooserRetryLoop, "_total_stats", FakeStats(11))
    orig_n = _set_class_property(ChooserRetryLoop, "_n_attempts", 0)

    try:
        loop = ChooserRetryLoop(cfg, problem_statement=None)
        # replace logger to capture message
        log = DummyLogger()
        loop.logger = log

        res = loop.retry()

        assert res is False
        # message must mention cost limit and instance cost
        assert any("exceeds cost limit" in m or "exceeds cost limit" in m.lower() for m in log.infos)
    finally:
        _restore_class_attr(ChooserRetryLoop, "_total_stats", orig_stats)
        _restore_class_attr(ChooserRetryLoop, "_n_attempts", orig_n)
        _restore_module_chooser(orig_module_chooser)


def test_retry_returns_false_when_max_attempts_reached_round_026():
    """Covers branch: self._n_attempts >= self._config.max_attempts > 0 -> False
    """
    cfg = SimpleNamespace(cost_limit=100, max_attempts=2, min_budget_for_new_attempt=0, chooser=SimpleNamespace())

    # patch module Chooser
    orig_module_chooser = _patch_module_chooser(DummyChooser)

    # total cost low so cost-limit branch not hit
    orig_stats = _set_class_property(ChooserRetryLoop, "_total_stats", FakeStats(10))
    # simulate attempts equal to max_attempts
    orig_n = _set_class_property(ChooserRetryLoop, "_n_attempts", 2)

    try:
        loop = ChooserRetryLoop(cfg, problem_statement=None)
        log = DummyLogger()
        loop.logger = log

        res = loop.retry()

        assert res is False
        # confirm logger captured a message about max_attempts
        assert any("max_attempts" in m or "max_attempts" in m.lower() for m in log.infos)
    finally:
        _restore_class_attr(ChooserRetryLoop, "_total_stats", orig_stats)
        _restore_class_attr(ChooserRetryLoop, "_n_attempts", orig_n)
        _restore_module_chooser(orig_module_chooser)


def test_retry_returns_false_when_not_enough_remaining_budget_round_026():
    """Covers branch: min_budget_for_new_attempt > 0 and remaining_budget < min_budget_for_new_attempt -> False
    """
    cfg = SimpleNamespace(cost_limit=100, max_attempts=10, min_budget_for_new_attempt=10, chooser=SimpleNamespace())

    # patch module Chooser
    orig_module_chooser = _patch_module_chooser(DummyChooser)

    # set instance cost so remaining budget is 5 < required 10
    orig_stats = _set_class_property(ChooserRetryLoop, "_total_stats", FakeStats(95))
    # attempts low so max_attempts branch not hit
    orig_n = _set_class_property(ChooserRetryLoop, "_n_attempts", 1)

    try:
        loop = ChooserRetryLoop(cfg, problem_statement=None)
        log = DummyLogger()
        loop.logger = log

        res = loop.retry()

        assert res is False
        # logger message contains not enough budget wording
        assert any("Not enough budget" in m or "not enough budget" in m.lower() for m in log.infos)
        # also check the remaining budget number appears in the message
        assert any("5" in m for m in log.infos)
    finally:
        _restore_class_attr(ChooserRetryLoop, "_total_stats", orig_stats)
        _restore_class_attr(ChooserRetryLoop, "_n_attempts", orig_n)
        _restore_module_chooser(orig_module_chooser)


def test_retry_returns_true_when_all_conditions_allow_new_attempt_round_026():
    """Covers final branch where retry() returns True
    """
    cfg = SimpleNamespace(cost_limit=1000, max_attempts=10, min_budget_for_new_attempt=1, chooser=SimpleNamespace())

    # patch module Chooser
    orig_module_chooser = _patch_module_chooser(DummyChooser)

    # very small instance cost so remaining budget > min required
    orig_stats = _set_class_property(ChooserRetryLoop, "_total_stats", FakeStats(10))
    orig_n = _set_class_property(ChooserRetryLoop, "_n_attempts", 1)

    try:
        loop = ChooserRetryLoop(cfg, problem_statement=None)
        # capture logs but expect none that cause an early exit
        log = DummyLogger()
        loop.logger = log

        res = loop.retry()

        assert res is True
        # ensure none of the early-exit messages were logged
        assert not any("exceeds cost limit" in m.lower() for m in log.infos)
        assert not any("max_attempts" in m.lower() for m in log.infos)
        assert not any("not enough budget" in m.lower() for m in log.infos)
    finally:
        _restore_class_attr(ChooserRetryLoop, "_total_stats", orig_stats)
        _restore_class_attr(ChooserRetryLoop, "_n_attempts", orig_n)
        _restore_module_chooser(orig_module_chooser)
