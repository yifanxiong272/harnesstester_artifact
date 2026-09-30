import types
from pathlib import Path
from sweagent.run.run_batch import RunBatch


def _make_fake_instance(pid):
    return types.SimpleNamespace(problem_statement=types.SimpleNamespace(id=pid))


def test_main_single_worker_round_125(monkeypatch, tmp_path):
    # Arrange: prepare a fake self object with the exact attributes RunBatch.main expects
    logs = []
    start_called = []
    end_called = []
    single_called = []
    multi_called = []
    merge_calls = []

    fake_self = types.SimpleNamespace()
    fake_self.logger = types.SimpleNamespace(info=lambda *a, **k: logs.append(a))
    fake_self._chooks = types.SimpleNamespace(
        on_start=lambda: start_called.append(True),
        on_end=lambda: end_called.append(True),
    )

    # When num_workers <= 1, main_single_worker should be called
    fake_self._num_workers = 1
    fake_self.main_single_worker = lambda: single_called.append(True)
    # Provide a multi-worker handler so we can assert it is not called
    fake_self.main_multi_worker = lambda: multi_called.append(True)

    fake_self.output_dir = tmp_path
    fake_self.instances = [_make_fake_instance("probA"), _make_fake_instance("probB")]

    # Patch merge_predictions at module level to capture calls
    def fake_merge(output_dirs, preds_path):
        merge_calls.append((list(output_dirs), preds_path))

    monkeypatch.setattr("sweagent.run.run_batch.merge_predictions", fake_merge)

    # Act
    RunBatch.main(fake_self)

    # Assert: hooks called
    assert start_called == [True], "on_start should be called once"
    assert end_called == [True], "on_end should be called once"

    # Assert: correct worker path invoked
    assert single_called == [True], "main_single_worker should be invoked for _num_workers == 1"
    assert multi_called == [], "main_multi_worker should NOT be invoked for _num_workers == 1"

    # Assert: logger.info was called with the output_dir as a formatting argument
    assert any(len(t) >= 2 and t[1] == tmp_path for t in logs), "logger.info should be called with output_dir"

    # Assert: merge_predictions was called once with expected output directories and preds.json path
    assert len(merge_calls) == 1
    out_dirs, preds = merge_calls[0]
    expected = [tmp_path / "probA", tmp_path / "probB"]
    assert out_dirs == expected
    assert preds == tmp_path / "preds.json"


def test_main_multi_worker_round_125(monkeypatch, tmp_path):
    # Arrange: similar fake self but trigger the multi-worker branch
    start_called = []
    end_called = []
    single_called = []
    multi_called = []
    merge_calls = []

    fake_self = types.SimpleNamespace()
    fake_self.logger = types.SimpleNamespace(info=lambda *a, **k: None)
    fake_self._chooks = types.SimpleNamespace(
        on_start=lambda: start_called.append(True),
        on_end=lambda: end_called.append(True),
    )

    fake_self._num_workers = 2
    fake_self.main_single_worker = lambda: single_called.append(True)
    fake_self.main_multi_worker = lambda: multi_called.append(True)

    fake_self.output_dir = tmp_path
    fake_self.instances = [_make_fake_instance("x")]

    def fake_merge(output_dirs, preds_path):
        merge_calls.append((list(output_dirs), preds_path))

    monkeypatch.setattr("sweagent.run.run_batch.merge_predictions", fake_merge)

    # Act
    RunBatch.main(fake_self)

    # Assert: hooks called
    assert start_called == [True]
    assert end_called == [True]

    # Assert: multi-worker path taken
    assert multi_called == [True]
    assert single_called == [], "main_single_worker should NOT be invoked for _num_workers > 1"

    # merge_predictions called and received expected single output dir
    assert len(merge_calls) == 1
    out_dirs, preds = merge_calls[0]
    assert out_dirs == [tmp_path / "x"]
    assert preds == tmp_path / "preds.json"
