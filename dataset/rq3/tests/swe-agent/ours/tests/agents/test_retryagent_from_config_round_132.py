import pytest
from sweagent.agent import agents


def test_from_config_with_object_round_132():
    """Ensure RetryAgent.from_config returns an instance of the calling class
    and that the provided config object is passed through unchanged.
    """
    class DummyRetry(agents.RetryAgent):
        def __init__(self, config):
            # capture the config passed in so we can assert it was forwarded
            self.captured = config

    sentinel = object()
    inst = DummyRetry.from_config(sentinel)

    # returned instance must be of the subclass that invoked the classmethod
    assert isinstance(inst, DummyRetry)
    # and the exact object passed to from_config must have been forwarded
    assert inst.captured is sentinel


def test_from_config_with_dict_round_132():
    """A second deterministic case: pass a simple dict as config and verify
    it is forwarded unchanged to the subclass __init__.
    """
    class DummyRetry2(agents.RetryAgent):
        def __init__(self, config):
            # store a shallow copy to demonstrate the exact object is provided
            self.captured = config

    cfg = {"retries": 3, "timeout": None}
    inst = DummyRetry2.from_config(cfg)

    assert isinstance(inst, DummyRetry2)
    # identity check: the same dict object should be forwarded
    assert inst.captured is cfg
