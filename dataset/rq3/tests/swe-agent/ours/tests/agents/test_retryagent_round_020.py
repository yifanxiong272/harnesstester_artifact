import copy
import importlib
import pytest


MODULE_PATH = "sweagent.agent.agents"


def make_retry_agent_instance():
    """Create an uninitialized RetryAgent instance (skip __init__) for targeted testing.
    The tests will set attributes required by get_trajectory_data manually.
    """
    mod = importlib.import_module(MODULE_PATH)
    RetryAgent = mod.RetryAgent
    inst = object.__new__(RetryAgent)
    return mod, inst


def test_assert_rloop_not_none_round_020():
    """Calling get_trajectory_data with no _rloop must fail the assert at the top of the function."""
    mod, inst = make_retry_agent_instance()
    # ensure attribute exists and is None to exercise the assertion
    inst._rloop = None
    with pytest.raises(AssertionError):
        inst.get_trajectory_data(False)


def test_choose_with_chooser_output_round_020(monkeypatch):
    """When choose=True and rloop is a ChooserRetryLoop with _chooser_output,
    the returned data should merge the selected attempt and include chooser/model stats.
    """
    mod, inst = make_retry_agent_instance()

    # Fake objects used by the code under test
    class FakeModelStats:
        def __init__(self, payload):
            self._payload = payload

        def model_dump(self):
            # deterministic dump
            return dict(self._payload)

    class FakeChooserOutput:
        def model_dump(self):
            return {"chooser_key": "chooser_value"}

    class FakeChooserRetryLoop:
        def __init__(self):
            self.review_model_stats = FakeModelStats({"rm": 1})
            self._chooser_output = FakeChooserOutput()

        def get_best(self):
            return 1

    # Ensure isinstance(..., ChooserRetryLoop) returns True for FakeChooserRetryLoop
    monkeypatch.setattr(mod, "ChooserRetryLoop", FakeChooserRetryLoop)

    # Setup instance state expected by get_trajectory_data
    rloop = FakeChooserRetryLoop()
    inst._rloop = rloop
    # Two attempts: index 0 and 1. Chosen index will be 1.
    inst._attempt_data = [
        {"info": {"attempt": 0}, "value": "first"},
        {"info": {"attempt": 1}, "value": "second"},
    ]
    inst._total_instance_stats = FakeModelStats({"total": 99})
    # logger is not used in success path, but attach a dummy to be safe
    inst.logger = type("L", (), {"critical": lambda *a, **k: None})()

    data = inst.get_trajectory_data(True)

    # Base structure preserved
    assert data["attempts"] is inst._attempt_data

    # The chosen attempt was merged into top-level data
    assert data["value"] == "second"

    # Info contains best_attempt_idx and the stats we provided
    assert data["info"]["best_attempt_idx"] == 1
    assert data["info"]["rloop_model_stats"] == {"rm": 1}
    assert data["info"]["model_stats"] == {"total": 99}

    # Chooser output included
    assert data["info"]["chooser"] == {"chooser_key": "chooser_value"}


def test_choose_handles_generic_exception_and_nonchooser_round_020(monkeypatch):
    """If rloop.get_best raises a generic Exception, we log and set best_attempt_idx to 0.
    Also ensure when rloop is not a ChooserRetryLoop, the 'chooser' key is not added.
    """
    mod, inst = make_retry_agent_instance()

    class FakeModelStats:
        def __init__(self, payload):
            self._payload = payload

        def model_dump(self):
            return dict(self._payload)

    class RaisingRloop:
        def __init__(self):
            self.review_model_stats = FakeModelStats({"rm": 7})
            # no _chooser_output attribute

        def get_best(self):
            raise RuntimeError("bogus")

    # Ensure ChooserRetryLoop is some unrelated class so isinstance(...) is False
    class SomeOtherChooser:
        pass

    monkeypatch.setattr(mod, "ChooserRetryLoop", SomeOtherChooser)

    rloop = RaisingRloop()
    inst._rloop = rloop
    inst._attempt_data = [
        {"info": {"attempt": 0}, "value": "first"},
        {"info": {"attempt": 1}, "value": "second"},
    ]
    inst._total_instance_stats = FakeModelStats({"total": 5})

    # Replace logger to capture calls
    class CapturingLogger:
        def __init__(self):
            self.calls = []

        def critical(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    logger = CapturingLogger()
    inst.logger = logger

    data = inst.get_trajectory_data(True)

    # Best index falls back to 0
    assert data["info"]["best_attempt_idx"] == 0

    # The rloop model stats are still recorded even after the exception
    assert data["info"]["rloop_model_stats"] == {"rm": 7}

    # Model stats overwritten by total_instance_stats
    assert data["info"]["model_stats"] == {"total": 5}

    # Because rloop is not instance of ChooserRetryLoop, chooser key should be absent
    assert "chooser" not in data["info"]

    # Ensure logger was called to report the error
    assert any("Error getting best attempt index" in str(args[0]) or "bogus" in str(args) for args, _ in logger.calls)


def test_choose_reraises_totalcostlimit_round_020(monkeypatch):
    """If get_best raises TotalCostLimitExceededError, it should be re-raised unchanged."""
    mod, inst = make_retry_agent_instance()

    # Import the exact exception used by the module to ensure correct type checking
    from sweagent.exceptions import TotalCostLimitExceededError

    class RloopRaisesTotalCost:
        def __init__(self):
            self.review_model_stats = type("S", (), {"model_dump": lambda s: {}})()

        def get_best(self):
            raise TotalCostLimitExceededError("limit reached")

    rloop = RloopRaisesTotalCost()
    inst._rloop = rloop
    inst._attempt_data = [{"info": {}, "value": "first"}]
    inst._total_instance_stats = type("T", (), {"model_dump": lambda s: {}})()
    inst.logger = type("L", (), {"critical": lambda *a, **k: None})()

    with pytest.raises(TotalCostLimitExceededError):
        inst.get_trajectory_data(True)
