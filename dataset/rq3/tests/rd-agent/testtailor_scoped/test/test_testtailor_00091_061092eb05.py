import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.data_science.workflow.__init__')
except Exception:
    _testtailor_target = None
else:
    globals().update({
        name: value
        for name, value in vars(_testtailor_target).items()
        if not name.startswith("__")
    })

class _TestTailorTimeout:
    @staticmethod
    def timeout(_seconds):
        return lambda function: function

timeout_decorator = _TestTailorTimeout()

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_case_XX(self):
        """Test implement_one_task uses queried knowledge and generates new workflow code."""
        # prepare a minimal WorkflowTask
        target_task = WorkflowTask()

        # prepare queried_knowledge with the attributes expected by the method under test
        class KnowledgeImpl:
            def __init__(self, code):
                self.file_dict = {"main.py": code}

        class Knowledge:
            def __init__(self, impl):
                self.implementation = impl

        info = target_task.get_task_information()
        class QK:
            pass

        qk = QK()
        # similar successful knowledge (not used deeply in this test, just ensure present)
        qk.task_to_similar_task_successful_knowledge = {info: ["successful_example"]}
        # former failed traces: a tuple (list_of_knowledge, meta)
        # include one knowledge with different main.py and one with same main.py to test filtering
        k_diff = Knowledge(KnowledgeImpl("print('old')"))
        k_same = Knowledge(KnowledgeImpl("print('same')"))
        qk.task_to_former_failed_traces = {info: ([k_diff, k_same], "meta")}

        # Minimal workspace-like object with file_dict and get_codes
        class WS:
            def __init__(self):
                self.file_dict = {
                    "main.py": "print('same')",
                    "load_data.py": "load",
                    "feature.py": "feat",
                    "ensemble.py": "ens",
                    "spec/workflow.md": "spec",
                    "EDA.md": "eda",
                }

            def get_codes(self, pattern):
                # mimic FBWorkspace.get_codes formatting for matching .py files
                import re

                filtered = {
                    k: v
                    for k, v in self.file_dict.items()
                    if re.search(pattern, k) and k.endswith(".py") and "test" not in k
                }
                s = ""
                for fn in sorted(filtered.keys()):
                    s += f"\nFile Path: {fn}\n```\n{filtered[fn]}\n```"
                return s

        ws = WS()

        prev = None  # no previous feedback

        # Retrieve the unbound method and access its globals to monkeypatch heavy dependencies
        method = WorkflowMultiProcessEvolvingStrategy.implement_one_task
        g = method.__globals__

        # Backup original globals to restore later
        old_T = g.get("T")
        old_APIBackend = g.get("APIBackend")
        old_PythonAgentOut = g.get("PythonAgentOut")
        old_DS_RD_SETTING = g.get("DS_RD_SETTING")

        # Dummy template helper that returns something when .r(...) is called
        class DummyT:
            def __init__(self, *a, **k):
                pass

            def r(self, **kwargs):
                return "DUMMY_PROMPT"

        # Dummy APIBackend that returns a string containing a python code block
        class DummyAPIBackend:
            def build_messages_and_create_chat_completion(self, user_prompt, system_prompt):
                return "```python\nprint('new')\n```"

        # Dummy PythonAgentOut that extracts the code block (consistent with DummyAPIBackend)
        class DummyPythonAgentOut:
            @classmethod
            def get_spec(cls):
                return "spec"

            @classmethod
            def extract_output(cls, resp: str):
                # return the expected code contained in the dummy response
                return "print('new')"

        # Dummy DS_RD_SETTING with spec_enabled True to follow one branch
        class DummyDSSetting:
            spec_enabled = True

        # Apply monkeypatches
        g["T"] = lambda *a, **k: DummyT()
        g["APIBackend"] = DummyAPIBackend
        g["PythonAgentOut"] = DummyPythonAgentOut
        g["DS_RD_SETTING"] = DummyDSSetting

        # Create fake self with required scen attribute
        class FakeScen:
            def get_scenario_all_desc(self, eda_output=None):
                return "competition_info"

        fake_self = type("FakeSelf", (), {"scen": FakeScen()})()

        try:
            res = method(fake_self, target_task, qk, ws, prev)
            # verify the returned dict contains main.py and the generated code
            self.assertIsInstance(res, dict)
            self.assertIn("main.py", res)
            self.assertEqual(res["main.py"], "print('new')")
        finally:
            # restore globals
            if old_T is not None:
                g["T"] = old_T
            else:
                g.pop("T", None)
            if old_APIBackend is not None:
                g["APIBackend"] = old_APIBackend
            else:
                g.pop("APIBackend", None)
            if old_PythonAgentOut is not None:
                g["PythonAgentOut"] = old_PythonAgentOut
            else:
                g.pop("PythonAgentOut", None)
            if old_DS_RD_SETTING is not None:
                g["DS_RD_SETTING"] = old_DS_RD_SETTING
            else:
                g.pop("DS_RD_SETTING", None)
