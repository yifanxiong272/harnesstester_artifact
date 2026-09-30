# file: rdagent/components/coder/data_science/raw_data_loader/__init__.py:59-179
# asked: {"lines": [68, 69, 70, 72, 73, 74, 75, 77, 78, 79, 80, 82, 83, 84, 85, 86, 88, 93, 94, 95, 96, 97, 98, 99, 101, 102, 104, 105, 107, 108, 109, 111, 112, 115, 117, 118, 119, 120, 121, 123, 124, 125, 126, 127, 130, 131, 132, 133, 134, 136, 137, 139, 140, 141, 144, 145, 146, 147, 148, 149, 152, 153, 154, 155, 156, 159, 160, 162, 164, 166, 167, 168, 169, 170, 171, 172, 173, 176, 177], "branches": [[93, 94], [93, 130], [94, 95], [94, 123], [152, 153], [152, 164], [159, 160], [159, 162]]}
# gained: {"lines": [68, 69, 70, 72, 73, 74, 77, 78, 79, 82, 83, 84, 85, 86, 88, 93, 94, 95, 96, 97, 98, 99, 101, 102, 104, 105, 107, 108, 109, 111, 112, 115, 117, 118, 119, 120, 121, 130, 131, 132, 133, 134, 136, 137, 139, 140, 141, 144, 145, 146, 147, 148, 149, 152, 153, 154, 155, 156, 159, 160, 162, 164, 166, 167, 168, 169, 170, 171, 172, 173, 176, 177], "branches": [[93, 94], [93, 130], [94, 95], [152, 153], [152, 164], [159, 160], [159, 162]]}

import types
from types import SimpleNamespace

import pytest


def _make_fake_T(call_log):
    class FakeT:
        def __init__(self, name):
            self.name = name

        def r(self, **kwargs):
            # record the call for assertions and return a simple string
            call_log.append((self.name, dict(kwargs)))
            return f"T({self.name})::{kwargs}"

    def factory(name):
        return FakeT(name)

    return factory


class FakeChatSession:
    def __init__(self, *args, **kwargs):
        pass

    def build_chat_completion(self, user_prompt=None, **kwargs):
        # return different spec bodies depending on user_prompt for clarity
        return f"SPEC_FOR::{user_prompt}"


class FakeAPIBackend:
    def __init__(self, *args, **kwargs):
        pass

    def build_chat_session(self, session_system_prompt=None):
        return FakeChatSession()

    def build_messages_and_create_chat_completion(self, user_prompt=None, system_prompt=None, **kwargs):
        # return a placeholder that PythonAgentOut.extract_output will interpret
        return {"user_prompt": user_prompt, "system_prompt": system_prompt}


class FakePythonAgentOut:
    @staticmethod
    def get_spec():
        return "PY_AGENT_SPEC"

    @staticmethod
    def extract_output(response):
        # default; tests will monkeypatch this method as needed
        return response.get("user_prompt", "CODE_FROM_API")


class DummyKnowledge:
    def __init__(self, impl_file_content):
        self.implementation = SimpleNamespace(file_dict={"load_data.py": impl_file_content})


class DummyDataLoaderTask:
    def __init__(self, info):
        self._info = info

    def get_task_information(self):
        return self._info


class DummyWorkspace:
    def __init__(self, file_dict):
        self.file_dict = dict(file_dict)


def _setup_common(monkeypatch, call_log):
    """
    Monkeypatch things in the target module to controllable fakes and return the module.
    """
    import rdagent.components.coder.data_science.raw_data_loader as rdr_mod

    # monkeypatch T used in module
    monkeypatch.setattr(rdr_mod, "T", _make_fake_T(call_log), raising=True)

    # monkeypatch APIBackend and PythonAgentOut
    monkeypatch.setattr(rdr_mod, "APIBackend", FakeAPIBackend, raising=True)
    monkeypatch.setattr(rdr_mod, "PythonAgentOut", FakePythonAgentOut, raising=True)

    return rdr_mod


class FakeScen:
    def __init__(self):
        self.processed_data_folder_description = "DATA_FOLDER_INFO"

    def get_scenario_all_desc(self, eda_output=None):
        return f"COMP_INFO::{eda_output}"

    def get_runtime_environment(self):
        return "RUNTIME_ENV"


def test_implement_one_task_with_spec_enabled(monkeypatch):
    call_log = []
    rdr_mod = _setup_common(monkeypatch, call_log)

    # Ensure DS_RD_SETTING.spec_enabled True in the module namespace
    monkeypatch.setattr(rdr_mod, "DS_RD_SETTING", SimpleNamespace(spec_enabled=True), raising=False)

    # Prepare a workspace with an existing older load_data.py so generation must produce a new one
    workspace = DummyWorkspace({"EDA.md": "eda content", "load_data.py": "old-code"})

    # Prepare target task
    target_task = DummyDataLoaderTask("my_task_info")

    # Prepare queried_knowledge with one similar successful and two former failed (one same code, one different)
    same_code_knowledge = DummyKnowledge("old-code")
    different_code_knowledge = DummyKnowledge("different-code")

    queried_knowledge = SimpleNamespace(
        task_to_similar_task_successful_knowledge={target_task.get_task_information(): ["sim_success"]},
        task_to_former_failed_traces={target_task.get_task_information(): ([same_code_knowledge, different_code_knowledge], "meta")},
    )

    # Make the PythonAgentOut.extract_output return a new code different from workspace to break loop immediately
    def extract_output_once(response):
        return "new-generated-code"

    monkeypatch.setattr(rdr_mod.PythonAgentOut, "extract_output", staticmethod(extract_output_once), raising=True)

    # instantiate with required scen and settings
    evo = rdr_mod.DataLoaderMultiProcessEvolvingStrategy(FakeScen(), SimpleNamespace())

    result = evo.implement_one_task(target_task=target_task, queried_knowledge=queried_knowledge, workspace=workspace, prev_task_feedback=None)

    # Assert returned dict contains spec files and load_data.py
    assert isinstance(result, dict)
    assert result["load_data.py"] == "new-generated-code"
    # since spec_enabled True, spec files should be included
    expected_spec_keys = {"spec/data_loader.md", "spec/feature.md", "spec/model.md", "spec/ensemble.md", "spec/workflow.md"}
    assert expected_spec_keys.issubset(set(result.keys()))

    # Also assert that T.r was called and that the queried_former_failed_knowledge got filtered:
    system_calls = [c for c in call_log if ".prompts:data_loader_coder.system" in c[0]]
    assert system_calls, "Expected system prompt generation call to be logged"
    kwargs = system_calls[-1][1]
    qffk = kwargs.get("queried_former_failed_knowledge")
    assert isinstance(qffk, list)
    assert len(qffk) == 1


def test_implement_one_task_with_spec_disabled(monkeypatch):
    call_log = []
    rdr_mod = _setup_common(monkeypatch, call_log)

    # Disable spec
    monkeypatch.setattr(rdr_mod, "DS_RD_SETTING", SimpleNamespace(spec_enabled=False), raising=False)

    # Provide a fake DIRNAME that supports the / operator and read_text to avoid file IO
    class FakePath:
        def __truediv__(self, other):
            return self

        def read_text(self):
            return "DUMMY_TEST_CODE"

    monkeypatch.setattr(rdr_mod, "DIRNAME", FakePath(), raising=False)

    # Prepare workspace with existing file and also include spec files to simulate presence (should be ignored)
    workspace = DummyWorkspace({"load_data.py": "old-code", "spec/data_loader.md": "existing_dl_spec"})

    target_task = DummyDataLoaderTask("task_no_spec")

    # Provide a queried_knowledge structure (must not be None) to avoid index errors in code
    queried_knowledge = SimpleNamespace(
        task_to_similar_task_successful_knowledge={target_task.get_task_information(): []},
        task_to_former_failed_traces={target_task.get_task_information(): ([], None)},
    )

    # Make PythonAgentOut.extract_output return new code != old-code
    monkeypatch.setattr(rdr_mod.PythonAgentOut, "extract_output", staticmethod(lambda resp: "generated-code-2"), raising=True)

    evo = rdr_mod.DataLoaderMultiProcessEvolvingStrategy(FakeScen(), SimpleNamespace())

    result = evo.implement_one_task(target_task=target_task, queried_knowledge=queried_knowledge, workspace=workspace, prev_task_feedback=None)

    # When spec is disabled, only load_data.py should be returned
    assert result == {"load_data.py": "generated-code-2"}


def test_implement_one_task_raises_when_no_new_code(monkeypatch):
    call_log = []
    rdr_mod = _setup_common(monkeypatch, call_log)

    # Choose spec enabled to exercise spec generation path
    monkeypatch.setattr(rdr_mod, "DS_RD_SETTING", SimpleNamespace(spec_enabled=True), raising=False)

    # workspace with existing code that API will keep returning
    workspace = DummyWorkspace({"load_data.py": "always-same"})

    target_task = DummyDataLoaderTask("task_raise")

    # Provide queried_knowledge non-None to avoid index error
    queried_knowledge = SimpleNamespace(
        task_to_similar_task_successful_knowledge={target_task.get_task_information(): []},
        task_to_former_failed_traces={target_task.get_task_information(): ([], None)},
    )

    # Force PythonAgentOut.extract_output to always return the same as workspace to trigger the 5-iteration failure
    monkeypatch.setattr(rdr_mod.PythonAgentOut, "extract_output", staticmethod(lambda resp: "always-same"), raising=True)

    evo = rdr_mod.DataLoaderMultiProcessEvolvingStrategy(FakeScen(), SimpleNamespace())

    with pytest.raises(rdr_mod.CoderError):
        evo.implement_one_task(target_task=target_task, queried_knowledge=queried_knowledge, workspace=workspace, prev_task_feedback=None)
