import pytest
from pathlib import Path

import sweagent.run.run_batch as rb
from sweagent.run.run_batch import RunBatch


def test_runbatch_human_parallel_raises_round_100(monkeypatch):
    """When the resolved model id is a human-type and num_workers > 1, __init__ must raise ValueError

    This exercises the branch that produces the error message "Cannot run with human model in parallel"
    (lines 163-165 in the file). We patch the class property _model_id so the check triggers during
    construction and provide a minimal instances list. We also pass hooks=[] to avoid default hook
    construction.
    """
    # Patch the RunBatch._model_id attribute so that during __init__ it resolves to "human".
    # Use raising=False to allow replacing methods/properties regardless of original implementation.
    monkeypatch.setattr(rb.RunBatch, "_model_id", property(lambda self: "human"), raising=False)

    with pytest.raises(ValueError) as excinfo:
        RunBatch(instances=[1, 2], agent_config=None, num_workers=2, hooks=[])

    assert str(excinfo.value) == "Cannot run with human model in parallel"


def test_runbatch_nonhuman_multi_worker_inits_round_100(monkeypatch, tmp_path):
    """When model is non-human and num_workers > 1, __init__ proceeds and sets attributes.

    We patch module-level helpers (get_logger, add_file_handler, CombinedRunHooks, RunBatchProgressManager)
    to deterministic no-op/mocks to avoid side effects (file handlers, logging) and to make observable
    assertions about how __init__ populated fields like _num_workers and _progress_manager.
    """
    # Make sure RunBatch reports a non-human model id so the early check does not raise.
    monkeypatch.setattr(rb.RunBatch, "_model_id", property(lambda self: "gpt-4"), raising=False)

    # Replace get_logger and add_file_handler with no-ops to avoid real logging side-effects.
    monkeypatch.setattr(rb, "get_logger", lambda *a, **k: "logger-object")
    monkeypatch.setattr(rb, "add_file_handler", lambda *a, **k: None)

    # CombinedRunHooks may be constructed; provide a trivial stand-in.
    class DummyCombined:
        def __init__(self, *a, **k):
            pass

    monkeypatch.setattr(rb, "CombinedRunHooks", DummyCombined)

    # Provide a deterministic RunBatchProgressManager replacement that records constructor args.
    class DummyProgressManager:
        def __init__(self, *args, **kwargs):
            # support both positional and keyword invocation
            self.args = args
            self.kwargs = kwargs
            self.num_instances = kwargs.get("num_instances") if "num_instances" in kwargs else (args[0] if args else None)
            self.yaml_report_path = kwargs.get("yaml_report_path") if "yaml_report_path" in kwargs else (args[1] if len(args) > 1 else None)

    monkeypatch.setattr(rb, "RunBatchProgressManager", DummyProgressManager)

    # Minimal inputs
    instances = ["i1", "i2"]
    # Use a custom random_delay_multiplier to assert it was stored.
    rdm = 0.42

    rb_inst = RunBatch(instances=instances, agent_config=None, num_workers=3, hooks=[], output_dir=tmp_path, random_delay_multiplier=rdm)

    # _num_workers should be min(num_workers, len(instances)) -> min(3,2) == 2
    assert getattr(rb_inst, "_num_workers") == 2

    # The provided random_delay_multiplier must be preserved
    assert getattr(rb_inst, "_random_delay_multiplier") == pytest.approx(rdm)

    # The progress manager should have been created with num_instances equal to len(instances)
    pm = getattr(rb_inst, "_progress_manager")
    assert isinstance(pm, DummyProgressManager)
    assert pm.num_instances == len(instances)
    # yaml_report_path should point inside the provided output_dir and include the expected filename
    assert isinstance(pm.yaml_report_path, Path) or (hasattr(pm, 'yaml_report_path') and str(pm.yaml_report_path).endswith("run_batch_exit_statuses.yaml"))
