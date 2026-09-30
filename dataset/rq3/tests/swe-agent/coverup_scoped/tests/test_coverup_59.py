# file: sweagent/run/run_batch.py:138-186
# asked: {"lines": [164, 165], "branches": [[163, 164]]}
# gained: {"lines": [164, 165], "branches": [[163, 164]]}

import pytest
from pathlib import Path

from sweagent.run.run_batch import RunBatch


@pytest.mark.parametrize("model_id", ["human", "human_thought"])
def test_runbatch_raises_for_human_models(monkeypatch, tmp_path, model_id):
    # Arrange: force the RunBatch._model_id property to return a human model id
    monkeypatch.setattr(RunBatch, "_model_id", property(lambda self: model_id))

    # Act / Assert: initializing with more than one worker must raise the specific ValueError
    with pytest.raises(ValueError, match="Cannot run with human model in parallel"):
        RunBatch(instances=[], agent_config=object(), output_dir=tmp_path, num_workers=2)


def test_runbatch_allows_human_model_with_single_worker(monkeypatch, tmp_path):
    # Arrange: force the RunBatch._model_id property to return 'human'
    monkeypatch.setattr(RunBatch, "_model_id", property(lambda self: "human"))

    # Provide one dummy instance so min(num_workers, len(instances)) yields 1
    dummy_instances = [object()]

    # Act: should not raise when num_workers == 1
    rb = RunBatch(instances=dummy_instances, agent_config=object(), output_dir=tmp_path, num_workers=1)

    # Assert: basic postconditions to ensure initialization proceeded
    assert rb.instances is dummy_instances
    assert rb.agent_config is not None
    # _num_workers should be min(num_workers, len(instances)) == 1
    assert rb._num_workers == 1
    # Output directory should be the tmp_path we passed
    assert Path(rb.output_dir) == tmp_path
