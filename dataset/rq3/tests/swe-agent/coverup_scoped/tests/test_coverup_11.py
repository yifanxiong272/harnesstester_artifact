# file: sweagent/agent/agents.py:327-352
# asked: {"lines": [329, 331, 332, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 347, 348, 349, 350, 352], "branches": [[335, 336], [335, 352], [348, 349], [348, 352]]}
# gained: {"lines": [329, 331, 332, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 347, 348, 349, 350, 352], "branches": [[335, 336], [335, 352], [348, 349]]}

import copy
import types
import pytest
from unittest.mock import Mock

from sweagent.agent import agents as agents_module
from sweagent.agent.agents import RetryAgent
from sweagent.exceptions import TotalCostLimitExceededError


def make_self(rloop, attempt_data, total_stats=None, logger=None):
    """
    Create a lightweight 'self' object suitable for calling RetryAgent.get_trajectory_data.
    We do not call any constructors; we simply create a SimpleNamespace-like object and
    attach attributes the method expects.
    """
    self_obj = types.SimpleNamespace()
    self_obj._rloop = rloop
    # deep copy to avoid accidental shared-state mutation across tests
    self_obj._attempt_data = copy.deepcopy(attempt_data)
    # model stats object must have model_dump method
    if total_stats is None:
        total_stats = types.SimpleNamespace(model_dump=lambda: {"total": "stats"})
    self_obj._total_instance_stats = total_stats
    # logger with critical method
    if logger is None:
        logger = Mock()
    self_obj.logger = logger
    return self_obj


def test_get_trajectory_data_choose_false_returns_attempts_only():
    # rloop can be anything non-None; choose=False should return just {'attempts': ...}
    dummy_rloop = object()
    attempts = [{"info": {}}, {"info": {}}]
    self_obj = make_self(dummy_rloop, attempts)
    result = RetryAgent.get_trajectory_data(self_obj, choose=False)
    assert result == {"attempts": attempts}


def test_get_trajectory_data_raises_total_cost_limit_exceeded():
    # create rloop whose get_best raises TotalCostLimitExceededError
    class RLoop:
        def get_best(self):
            raise TotalCostLimitExceededError("limit reached")

    rloop = RLoop()
    attempts = [{"info": {}}, {"info": {}}]
    self_obj = make_self(rloop, attempts)
    with pytest.raises(TotalCostLimitExceededError):
        RetryAgent.get_trajectory_data(self_obj, choose=True)


def test_get_trajectory_data_handles_generic_exception_and_chooser_output_present(monkeypatch):
    # Create a dummy class NOT inheriting from the real ChooserRetryLoop to avoid property/setter issues
    class DummyBase:
        def __init__(self):
            # make attributes writable on instance
            self._chooser_output = types.SimpleNamespace(model_dump=lambda: {"chooser": "out"})
            self.review_model_stats = types.SimpleNamespace(model_dump=lambda: {"review": "stats"})

        def get_best(self):
            raise ValueError("boom")

    # Monkeypatch the name used in agents module so isinstance check will succeed
    monkeypatch.setattr(agents_module, "ChooserRetryLoop", DummyBase)

    dummy = DummyBase()

    # attempt data with at least index 0 and info dict so the code can augment it
    attempts = [
        {"info": {"existing": "value"}, "attempt_meta": "a"},
        {"info": {}, "attempt_meta": "b"},
    ]

    # total instance stats
    total_stats = types.SimpleNamespace(model_dump=lambda: {"total": "s"})

    logger = Mock()

    self_obj = make_self(dummy, attempts, total_stats=total_stats, logger=logger)

    res = RetryAgent.get_trajectory_data(self_obj, choose=True)

    # Should have merged attempt_data[0] into top-level and kept attempts list
    assert "attempts" in res and res["attempts"] == attempts
    # Fields from attempt_data[0] should be present at top-level
    assert res.get("attempt_meta") == "a"
    # info should exist and include best_attempt_idx and existing info
    assert "info" in res
    assert res["info"]["best_attempt_idx"] == 0
    assert res["info"]["existing"] == "value"
    # model stats come from the provided objects
    assert res["info"]["rloop_model_stats"] == {"review": "stats"}
    assert res["info"]["model_stats"] == {"total": "s"}
    # chooser branch: chooser_output.model_dump used
    assert res["info"]["chooser"] == {"chooser": "out"}
    # logger.critical should have been called because get_best raised a generic exception
    logger.critical.assert_called()
    call_args = logger.critical.call_args[0]
    assert "Error getting best attempt index" in call_args[0]


def test_get_trajectory_data_chooser_output_none_results_in_empty_dict(monkeypatch):
    # Create a dummy class NOT inheriting from the real ChooserRetryLoop to avoid property/setter issues
    class DummyBase2:
        def __init__(self):
            self._chooser_output = None
            self.review_model_stats = types.SimpleNamespace(model_dump=lambda: {"review": "stats2"})

        def get_best(self):
            return 1

    monkeypatch.setattr(agents_module, "ChooserRetryLoop", DummyBase2)

    dummy = DummyBase2()

    attempts = [
        {"info": {}, "attempt_meta": "a"},
        {"info": {}, "attempt_meta": "b"},
    ]

    total_stats = types.SimpleNamespace(model_dump=lambda: {"total": "s2"})
    logger = Mock()
    self_obj = make_self(dummy, attempts, total_stats=total_stats, logger=logger)

    res = RetryAgent.get_trajectory_data(self_obj, choose=True)

    # best_attempt_idx should be 1 and attempt_meta from attempts[1] merged
    assert res["info"]["best_attempt_idx"] == 1
    assert res.get("attempt_meta") == "b"
    # chooser should be empty dict because _chooser_output is None
    assert res["info"]["chooser"] == {}
    # rloop and total model stats present
    assert res["info"]["rloop_model_stats"] == {"review": "stats2"}
    assert res["info"]["model_stats"] == {"total": "s2"}
