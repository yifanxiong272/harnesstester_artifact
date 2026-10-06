import pytest


def test_probe_001():
    # Import only the declared public entrypoint (the class that exposes the target method).
    from rdagent.components.coder.data_science.model import ModelMultiProcessEvolvingStrategy

    # Construct an instance without running potentially heavy __init__ logic.
    strategy = object.__new__(ModelMultiProcessEvolvingStrategy)

    # Provide the minimal scen the method expects.
    strategy.scen = type("S", (), {"get_scenario_all_desc": lambda self: "scenario-desc"})()

    # Minimal target_task with required attributes used by implement_one_task.
    class DummyTask:
        def __init__(self):
            self.name = "mymodel"

        def get_task_information(self):
            return "model_information_string"

    target_task = DummyTask()

    # Minimal workspace with file_dict entries the method will read.
    class DummyWorkspace:
        def __init__(self):
            self.file_dict = {
                "mymodel.py": "old_code",
                "feature.py": "feature code",
                "spec/model.md": "model spec",
                "load_data.py": "loader code",
            }

        def get_codes(self, pattern):
            # Return a deterministic value for latest_model_code lookup used by user_prompt construction.
            return {"model_v1.py": "code_v1"}

    workspace = DummyWorkspace()

    # Call the target method with queried_knowledge explicitly set to None (the optional value).
    # Primary oracle: this must not raise IndexError. If it does, the test fails, revealing the bug.
    try:
        _ = strategy.implement_one_task(target_task, queried_knowledge=None, workspace=workspace, prev_task_feedback=None)
    except IndexError as e:
        pytest.fail(
            "implement_one_task raised IndexError when queried_knowledge=None; optional parameter should be safe: " + str(e)
        )
