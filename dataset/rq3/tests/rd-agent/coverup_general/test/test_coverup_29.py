# file: rdagent/components/coder/CoSTEER/knowledge_management.py:270-339
# asked: {"lines": [276, 277, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 297, 298, 300, 301, 302, 303, 306, 307, 309, 310, 311, 312, 315, 316, 320, 321, 322, 323, 324, 327, 328, 329, 331, 332, 333, 334, 335, 338, 339], "branches": [[276, 277], [276, 280], [280, 281], [280, 338], [284, 280], [284, 285], [289, 290], [289, 291], [296, 284], [296, 300], [300, 301], [300, 306], [309, 310], [309, 320], [321, 322], [321, 327]]}
# gained: {"lines": [276, 277, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 297, 298, 300, 301, 302, 303, 306, 307, 309, 310, 311, 312, 315, 316, 320, 321, 322, 323, 324, 327, 328, 329, 331, 332, 333, 334, 335, 338, 339], "branches": [[276, 277], [276, 280], [280, 281], [280, 338], [284, 280], [284, 285], [289, 290], [289, 291], [296, 300], [300, 301], [309, 310], [309, 320], [321, 322], [321, 327]]}

import types
import pytest

from rdagent.components.coder.CoSTEER import knowledge_management as km


class DummyTask:
    def __init__(self, info):
        self._info = info

    def get_task_information(self):
        return self._info


class DummyImplementation:
    def __init__(self, name):
        self.name = name


class DummyFeedback:
    def __init__(self, final_decision, return_checking=None, execution=None):
        self.final_decision = final_decision
        self.return_checking = return_checking
        self.execution = execution


class DummyEvoStep:
    def __init__(self, implementations, feedback):
        self.evolvable_subjects = implementations
        self.feedback = feedback


class DummyImplementations:
    def __init__(self, tasks, workspaces):
        self.sub_tasks = tasks
        self.sub_workspace_list = workspaces


class DummyKnowledgebase:
    def __init__(self):
        self.success_task_to_knowledge_dict = {}
        self.task_to_component_nodes = {}
        self.working_trace_knowledge = {}
        self.working_trace_error_analysis = {}
        self.updated = []

    def update_success_task(self, task_info):
        # record calls for assertions
        self.updated.append(task_info)


def make_strategy_instance(monkeypatch):
    # Create instance without calling __init__
    inst = object.__new__(km.CoSTEERRAGStrategyV2)
    # minimal attributes required by generate_knowledge
    inst.current_generated_trace_count = 0
    inst.knowledgebase = DummyKnowledgebase()

    # provide analyze_component and analyze_error implementations
    def analyze_component(task_info):
        return [f"component_node_for_{task_info}"]

    def analyze_error(err, feedback_type="execution"):
        return [f"analyzed_{feedback_type}_{repr(err)}"]

    inst.analyze_component = analyze_component
    inst.analyze_error = analyze_error

    # Monkeypatch CoSTEERKnowledge in the module to a simple container to avoid relying on external class
    class _MockCoSTEERKnowledge:
        def __init__(self, target_task, implementation, feedback):
            self.target_task = target_task
            self.implementation = implementation
            self.feedback = feedback

        def __repr__(self):
            return f"<MockKnowledge {self.target_task.get_task_information()}>"

    monkeypatch.setattr(km, "CoSTEERKnowledge", _MockCoSTEERKnowledge, raising=False)

    return inst


def test_generate_knowledge_early_return(monkeypatch):
    inst = make_strategy_instance(monkeypatch)
    # current_generated_trace_count equals length of evolving_trace -> should return None early
    inst.current_generated_trace_count = 0
    evolving_trace = []
    result = km.CoSTEERRAGStrategyV2.generate_knowledge(inst, evolving_trace)
    assert result is None
    # ensure nothing was added to knowledgebase
    assert inst.knowledgebase.working_trace_knowledge == {}
    assert inst.knowledgebase.success_task_to_knowledge_dict == {}
    assert inst.knowledgebase.working_trace_error_analysis == {}


def test_generate_knowledge_all_branches(monkeypatch):
    inst = make_strategy_instance(monkeypatch)

    # Create tasks:
    # task0: final_decision True -> success path
    # task1: final_decision False with return_checking -> error value path
    # task2: final_decision False with no return_checking -> execution error path
    # task3: implementation is None -> should be skipped (continue)
    # task4: single_feedback is None -> should be skipped (continue)
    t0 = DummyTask("task0")
    t1 = DummyTask("task1")
    t2 = DummyTask("task2")
    t3 = DummyTask("task3")
    t4 = DummyTask("task4")

    impl0 = DummyImplementation("impl0")
    impl1 = DummyImplementation("impl1")
    impl2 = DummyImplementation("impl2")
    impl3 = None  # should be skipped
    impl4 = DummyImplementation("impl4")

    fb0 = DummyFeedback(final_decision=True, return_checking=None, execution=None)
    fb1 = DummyFeedback(final_decision=False, return_checking={"val": 123}, execution=None)
    fb2 = DummyFeedback(final_decision=False, return_checking=None, execution={"exc": "oops"})
    fb3 = DummyFeedback(final_decision=False, return_checking=None, execution=None)
    fb4 = None  # should be skipped

    implementations = DummyImplementations(
        tasks=[t0, t1, t2, t3, t4],
        workspaces=[impl0, impl1, impl2, impl3, impl4],
    )

    feedback_list = [fb0, fb1, fb2, fb3, fb4]

    evo_step = DummyEvoStep(implementations, feedback_list)
    evolving_trace = [evo_step]

    # preconditions
    assert inst.current_generated_trace_count == 0

    # run
    result = km.CoSTEERRAGStrategyV2.generate_knowledge(inst, evolving_trace)

    # method returns None
    assert result is None

    # current_generated_trace_count should be updated to length of evolving_trace (1)
    assert inst.current_generated_trace_count == len(evolving_trace)

    kb = inst.knowledgebase

    # working_trace_knowledge should have entries for t0, t1, t2, and t3? t3 skipped due impl None; t4 skipped due feedback None
    assert "task0" in kb.working_trace_knowledge
    assert "task1" in kb.working_trace_knowledge
    assert "task2" in kb.working_trace_knowledge
    assert "task3" not in kb.working_trace_knowledge
    assert "task4" not in kb.working_trace_knowledge

    # success_task_to_knowledge_dict should contain task0 because final_decision True
    assert "task0" in kb.success_task_to_knowledge_dict
    # update_success_task should have been called for task0
    assert kb.updated == ["task0"]

    # working_trace_error_analysis should contain analyses for task1 and task2
    assert "task1" in kb.working_trace_error_analysis
    assert "task2" in kb.working_trace_error_analysis
    # verify that analyze_error was called with appropriate types/formats via contents
    val_analysis = kb.working_trace_error_analysis["task1"][0]
    exec_analysis = kb.working_trace_error_analysis["task2"][0]
    assert isinstance(val_analysis, list) and val_analysis[0].startswith("analyzed_value_")
    assert isinstance(exec_analysis, list) and exec_analysis[0].startswith("analyzed_execution_")

    # task_to_component_nodes should have been filled for each task encountered (except skipped)
    assert kb.task_to_component_nodes["task0"] == ["component_node_for_task0"]
    assert kb.task_to_component_nodes["task1"] == ["component_node_for_task1"]
    assert kb.task_to_component_nodes["task2"] == ["component_node_for_task2"]
