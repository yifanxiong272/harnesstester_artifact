import copy
from types import SimpleNamespace
import pytest

from sweagent.agent.agents import RetryAgent, ChooserRetryLoop, TotalCostLimitExceededError

# We'll call the unbound function RetryAgent.get_trajectory_data and pass a lightweight
# dummy object as `self`. This avoids needing to construct full RetryAgent instances.
get_trajectory_data_fn = RetryAgent.get_trajectory_data


def test_get_trajectory_data_choose_false_round_022():
    """When choose is False, the method should return only the attempts mapping unchanged."""
    attempts = [{"info": {"meta": 1}, "value": "A"}]
    dummy = SimpleNamespace(
        _rloop=object(),  # just needs to be not None for the initial assert
        _attempt_data=attempts,
        logger=SimpleNamespace(),
        _total_instance_stats=SimpleNamespace(model_dump=lambda: {"total": "stats"}),
    )

    result = get_trajectory_data_fn(dummy, False)
    # Must be deterministic and directly observable
    assert result == {"attempts": attempts}


def test_get_trajectory_data_get_best_raises_non_total_round_022():
    """If get_best raises a non-TotalCostLimitExceededError, logger.critical is called and
    best_attempt_idx is set to 0. Also model_stats should be overwritten by _total_instance_stats."""
    attempts = [
        {"info": {"model_stats": {"old": True}}, "attempt_meta": 123},
        {"info": {}, "attempt_meta": 456},
    ]

    # rloop whose get_best raises a generic Exception
    def raising_get_best():
        raise ValueError("boom")

    logged = []
    dummy_logger = SimpleNamespace(critical=lambda *args, **kwargs: logged.append((args, kwargs)))

    rloop = SimpleNamespace(
        get_best=raising_get_best,
        review_model_stats=SimpleNamespace(model_dump=lambda: {"rloop": "stats"}),
        # Not a ChooserRetryLoop instance, so chooser branch isn't executed here
    )

    dummy = SimpleNamespace(
        _rloop=rloop,
        _attempt_data=attempts,
        logger=dummy_logger,
        _total_instance_stats=SimpleNamespace(model_dump=lambda: {"total": "overwritten"}),
    )

    result = get_trajectory_data_fn(dummy, True)

    # logger.critical should have been called due to the caught generic Exception
    assert logged, "logger.critical was not called when get_best raised an Exception"

    # best_attempt_idx should have been set to 0
    assert result["info"]["best_attempt_idx"] == 0

    # rloop model stats should be taken from review_model_stats
    assert result["info"]["rloop_model_stats"] == {"rloop": "stats"}

    # model_stats should be overwritten by _total_instance_stats.model_dump()
    assert result["info"]["model_stats"] == {"total": "overwritten"}

    # The returned data should include keys from the chosen attempt (index 0)
    assert result["attempt_meta"] == 123


def test_get_trajectory_data_get_best_raises_total_repropagates_round_022():
    """If get_best raises TotalCostLimitExceededError it should be re-raised to the caller."""
    attempts = [{"info": {}}, {"info": {}}]

    def raising_total():
        raise TotalCostLimitExceededError("limit")

    rloop = SimpleNamespace(get_best=raising_total, review_model_stats=SimpleNamespace(model_dump=lambda: {}))
    dummy = SimpleNamespace(
        _rloop=rloop,
        _attempt_data=attempts,
        logger=SimpleNamespace(),
        _total_instance_stats=SimpleNamespace(model_dump=lambda: {}),
    )

    with pytest.raises(TotalCostLimitExceededError):
        get_trajectory_data_fn(dummy, True)


def test_get_trajectory_data_with_chooser_output_none_round_022():
    """When _rloop is a ChooserRetryLoop and _chooser_output is None, chooser info should be {}."""
    attempts = [
        {"info": {}, "value": "first"},
        {"info": {}, "value": "second"},
    ]

    # Create a subclass of ChooserRetryLoop that shadows the review_model_stats property
    class FakeChooser(ChooserRetryLoop):
        # define a plain-class attribute to override the property on the base class
        review_model_stats = None

    rloop = object.__new__(FakeChooser)
    rloop.get_best = lambda: 1
    rloop.review_model_stats = SimpleNamespace(model_dump=lambda: {"choose": True})
    rloop._chooser_output = None

    dummy = SimpleNamespace(
        _rloop=rloop,
        _attempt_data=attempts,
        logger=SimpleNamespace(),
        _total_instance_stats=SimpleNamespace(model_dump=lambda: {"total": 0}),
    )

    result = get_trajectory_data_fn(dummy, True)
    # chooser key must exist and be the empty dict when _chooser_output is falsy
    assert result["info"]["chooser"] == {}
    # best index should be the one returned by get_best
    assert result["info"]["best_attempt_idx"] == 1


def test_get_trajectory_data_with_chooser_output_present_round_022():
    """When _rloop is a ChooserRetryLoop and _chooser_output is present, chooser info should be the model_dump result."""
    attempts = [
        {"info": {}, "value": "first"},
        {"info": {}, "value": "second"},
    ]

    class FakeChooser2(ChooserRetryLoop):
        review_model_stats = None

    rloop = object.__new__(FakeChooser2)
    rloop.get_best = lambda: 0
    rloop.review_model_stats = SimpleNamespace(model_dump=lambda: {"choose": True})
    rloop._chooser_output = SimpleNamespace(model_dump=lambda: {"chosen": 42})

    dummy = SimpleNamespace(
        _rloop=rloop,
        _attempt_data=attempts,
        logger=SimpleNamespace(),
        _total_instance_stats=SimpleNamespace(model_dump=lambda: {"total": 0}),
    )

    result = get_trajectory_data_fn(dummy, True)
    assert result["info"]["chooser"] == {"chosen": 42}
    assert result["info"]["best_attempt_idx"] == 0
