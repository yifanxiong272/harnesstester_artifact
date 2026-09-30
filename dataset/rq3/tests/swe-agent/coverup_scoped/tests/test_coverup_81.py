# file: sweagent/run/run_single.py:205-206
# asked: {"lines": [206], "branches": []}
# gained: {"lines": [206], "branches": []}

import pytest
from types import SimpleNamespace

from sweagent.run.run_single import run_from_config, RunSingle


def test_run_from_config_calls_from_config_and_run(monkeypatch):
    called = {}

    class DummyRunSingle:
        def __init__(self, config):
            # record that constructor got the config
            called['config_obj'] = config

        def run(self):
            # record that run was called
            called['ran'] = True
            return "done"

    # fake classmethod that will be bound as RunSingle.from_config
    def fake_from_config(cls, config):
        called['cls'] = cls
        return DummyRunSingle(config)

    monkeypatch.setattr(RunSingle, "from_config", classmethod(fake_from_config), raising=True)

    sentinel_config = SimpleNamespace(name="sentinel-config")
    result = run_from_config(sentinel_config)

    # run_from_config does not return anything; ensure run was invoked
    assert called.get('ran') is True
    # ensure the exact config object passed into run_from_config was forwarded
    assert called.get('config_obj') is sentinel_config
    # ensure the class passed to the classmethod is the RunSingle class
    assert called.get('cls') is RunSingle
    # run_from_config should return None
    assert result is None


def test_run_from_config_propagates_exceptions_from_run(monkeypatch):
    # ensure exceptions raised by run() are propagated by run_from_config
    class ErrRunSingle:
        def __init__(self, config):
            self.config = config

        def run(self):
            raise RuntimeError("run failed")

    def fake_from_config(cls, config):
        return ErrRunSingle(config)

    monkeypatch.setattr(RunSingle, "from_config", classmethod(fake_from_config), raising=True)

    with pytest.raises(RuntimeError, match="run failed"):
        run_from_config(object())
