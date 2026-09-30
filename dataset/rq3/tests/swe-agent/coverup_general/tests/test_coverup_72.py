# file: sweagent/run/run_batch.py:119-130
# asked: {"lines": [123, 124, 125, 129, 130], "branches": [[121, 123], [123, 124], [123, 130]]}
# gained: {"lines": [123, 124, 125, 129, 130], "branches": [[121, 123], [123, 124], [123, 130]]}

import pytest

from sweagent.run.run_batch import RunBatchConfig
from sweagent.run.batch_instances import SWEBenchInstances
from sweagent.agent.agents import DefaultAgentConfig
from sweagent.agent.models import InstantEmptySubmitModelConfig


def make_agent_config():
    return DefaultAgentConfig(model=InstantEmptySubmitModelConfig())


def test_evaluate_and_redo_existing_raises():
    # When instances is SWEBenchInstances and both evaluate and redo_existing are True,
    # the model_validator should raise a ValueError.
    instances = SWEBenchInstances(evaluate=True)
    with pytest.raises(ValueError) as excinfo:
        RunBatchConfig(instances=instances, agent=make_agent_config(), redo_existing=True)
    assert "Cannot evaluate and redo existing" in str(excinfo.value)


def test_evaluate_and_redo_existing_allows_other_combinations():
    # Case 1: evaluate True, redo_existing False -> allowed
    inst1 = SWEBenchInstances(evaluate=True)
    cfg1 = RunBatchConfig(instances=inst1, agent=make_agent_config(), redo_existing=False)
    assert cfg1.instances.evaluate is True
    assert cfg1.redo_existing is False

    # Case 2: evaluate False, redo_existing True -> allowed
    inst2 = SWEBenchInstances(evaluate=False)
    cfg2 = RunBatchConfig(instances=inst2, agent=make_agent_config(), redo_existing=True)
    assert cfg2.instances.evaluate is False
    assert cfg2.redo_existing is True
