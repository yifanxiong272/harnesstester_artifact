# file: sweagent/run/run_batch.py:256-266
# asked: {"lines": [264, 265, 266], "branches": [[259, 261]]}
# gained: {"lines": [264, 265, 266], "branches": []}

import pytest

from types import SimpleNamespace

def test_main_single_worker_enters_live_and_handles_break(monkeypatch):
    # Import inside test to ensure monkeypatching works on the module attributes used in __init__
    from sweagent.run import run_batch
    from sweagent.run.run_batch import RunBatch, _BreakLoop

    # Capture calls and state
    live_entered = {"entered": False, "exited": False}
    logger_calls = []

    # Dummy logger to capture info calls
    class DummyLogger:
        def info(self, msg):
            logger_calls.append(msg)

    dummy_logger = DummyLogger()

    # Monkeypatch get_logger to return our dummy logger
    monkeypatch.setattr(run_batch, "get_logger", lambda *a, **k: dummy_logger)

    # Monkeypatch add_file_handler to no-op to avoid filesystem interactions
    monkeypatch.setattr(run_batch, "add_file_handler", lambda *a, **k: None)

    # Dummy RunBatchProgressManager with required attribute render_group
    class DummyProgressManager:
        def __init__(self, num_instances, yaml_report_path):
            self.render_group = "dummy-render-group"

    monkeypatch.setattr(run_batch, "RunBatchProgressManager", DummyProgressManager)

    # Dummy Live context manager factory that records enter/exit
    def dummy_live_factory(renderable):
        class CM:
            def __enter__(self_nonlocal):
                live_entered["entered"] = True
                return self_nonlocal
            def __exit__(self_nonlocal, exc_type, exc, tb):
                live_entered["exited"] = True
                return False
        return CM()
    monkeypatch.setattr(run_batch, "Live", dummy_live_factory)

    # Prevent add_hook side effects during __init__
    monkeypatch.setattr(RunBatch, "add_hook", lambda self, hook: None)

    # Create a subclass that defines _model_id and run_instance to raise _BreakLoop
    class TB(RunBatch):
        def __init__(self, *args, **kwargs):
            # Ensure default progress_bar True so the Live branch is taken
            super().__init__(*args, **kwargs)
            self.run_calls = 0

        @property
        def _model_id(self):
            # Not 'human' or 'human_thought' so Live should be used
            return "gpt-test"

        def run_instance(self, instance):
            # Record call and then raise _BreakLoop to hit except branch
            self.run_calls += 1
            raise _BreakLoop()

    instances = ["i1", "i2"]

    # Construct the test RunBatch instance
    rb = TB(instances=instances, agent_config=None, output_dir=run_batch.Path("."), hooks=[], num_workers=1, progress_bar=True)

    # Execute main_single_worker which should enter Live and then break on _BreakLoop
    rb.main_single_worker()

    # Assertions to verify that the Live context was entered and that the break branch ran
    assert live_entered["entered"] is True, "Live context should have been entered"
    assert live_entered["exited"] is True, "Live context should have been exited"
    assert rb.run_calls == 1, "run_instance should have been called exactly once before breaking"
    # Logger should have received the stopping message
    assert any("Stopping loop over instances" in m for m in logger_calls), "Expected stopping log message"
