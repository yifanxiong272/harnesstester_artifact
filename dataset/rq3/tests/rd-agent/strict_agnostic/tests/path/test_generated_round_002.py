import importlib
from types import SimpleNamespace


def test_success_mapping_round_002():
    """
    Verify that when queried_knowledge contains a successful entry for the target task,
    evaluate returns that entry's .feedback immediately (covers lines ~134-139).
    """
    eval_mod = importlib.import_module("rdagent.components.coder.data_science.pipeline.eval")

    # Create an evaluator instance without running its __init__ and with minimal attributes
    evaluator = eval_mod.PipelineCoSTEEREvaluator.__new__(eval_mod.PipelineCoSTEEREvaluator)

    # Create a dummy Task that returns a stable task identifier
    target_task = SimpleNamespace(get_task_information=lambda: "task_success_id")

    # Create a simple sentinel feedback object and wrap it into the queried_knowledge structure
    sentinel_feedback = object()
    knowledge_entry = SimpleNamespace(feedback=sentinel_feedback)
    queried_knowledge = SimpleNamespace(
        success_task_to_knowledge_dict={"task_success_id": knowledge_entry},
        failed_task_info_set=set(),
        task_to_similar_task_successful_knowledge={},
    )

    # Call evaluate; because the success mapping exists it should return the sentinel feedback
    returned = eval_mod.PipelineCoSTEEREvaluator.evaluate(
        evaluator, target_task, implementation=None, gt_implementation=None, queried_knowledge=queried_knowledge
    )

    assert returned is sentinel_feedback


def test_failed_task_info_round_002():
    """
    Verify that when queried_knowledge indicates the task has failed many times,
    evaluate returns a PipelineSingleFeedback-like object with the expected fields
    (covers lines ~140-148).
    """
    eval_mod = importlib.import_module("rdagent.components.coder.data_science.pipeline.eval")

    evaluator = eval_mod.PipelineCoSTEEREvaluator.__new__(eval_mod.PipelineCoSTEEREvaluator)

    target_task = SimpleNamespace(get_task_information=lambda: "task_failed_id")

    queried_knowledge = SimpleNamespace(
        success_task_to_knowledge_dict={},
        failed_task_info_set={"task_failed_id"},
        task_to_similar_task_successful_knowledge={},
    )

    returned = eval_mod.PipelineCoSTEEREvaluator.evaluate(
        evaluator, target_task, implementation=None, gt_implementation=None, queried_knowledge=queried_knowledge
    )

    # The function constructs a PipelineSingleFeedback with specific fields.
    # Assert the most important observable behaviors deterministically.
    assert hasattr(returned, "final_decision")
    assert returned.final_decision is False

    assert hasattr(returned, "error_message")
    assert "This task has failed too many times" in returned.error_message

    # Also check textual fields are set to the standardized skip message
    assert getattr(returned, "execution", "").startswith("This task has failed too many times")
    assert getattr(returned, "return_checking", "").startswith("This task has failed too many times")
