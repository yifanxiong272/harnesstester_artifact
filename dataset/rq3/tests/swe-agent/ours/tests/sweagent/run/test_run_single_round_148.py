import builtins
import types
import sweagent.run.run_single as run_single


def test_run_from_config_calls_run_round_148(monkeypatch):
    """Ensure run_from_config calls RunSingle.from_config and then run().

    We patch RunSingle.from_config to return a lightweight object whose
    run() method records that it was called and captures the config
    that was forwarded. This isolates the test from heavy constructors
    or side effects.
    """
    called = {"ran": False}
    captured = {"cfg": None}

    class DummyRunObj:
        def __init__(self, cfg):
            # record the exact object passed so we can assert identity
            captured["cfg"] = cfg

        def run(self):
            called["ran"] = True

    # Define a replacement for the classmethod RunSingle.from_config
    def fake_from_config(cls, cfg):
        return DummyRunObj(cfg)

    # Patch the method where run_from_config resolves it
    monkeypatch.setattr(run_single.RunSingle, "from_config", classmethod(fake_from_config))

    sentinel = object()
    # Call the function under test; should use our patched from_config
    run_single.run_from_config(sentinel)

    # Oracle: the returned DummyRunObj.run() must have been called
    assert called["ran"] is True
    # Oracle: the same config object passed into run_from_config should be forwarded
    assert captured["cfg"] is sentinel
