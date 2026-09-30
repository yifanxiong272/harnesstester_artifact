import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.data_science.proposal.exp_gen.draft.draft')
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
        """Find the DSDraftExpGen class in the rdagent package, patch its T and APIBackend
        dependencies at the function globals and module level, and verify _init_task_gen
        returns the parsed JSON dict produced by the fake backend.
        """
        import importlib
        import json
        from pathlib import Path
        import pkgutil
        import rdagent

        target_cls = None
        target_module = None

        # Locate the DSDraftExpGen definition by walking package files to avoid pkgutil import quirks
        pkg_path = Path(list(rdagent.__path__)[0]) if hasattr(rdagent, "__path__") else Path(rdagent.__file__).parent

        for file in pkg_path.rglob("*.py"):
            try:
                rel = file.relative_to(pkg_path)
            except Exception:
                continue
            if rel.name == "__init__.py":
                module_name = rdagent.__name__
            else:
                module_name = rdagent.__name__ + "." + rel.with_suffix("").as_posix().replace("/", ".")
            # skip templates/examples heuristics
            if "example" in str(rel) or "tpl" in str(rel) or "template" in str(rel):
                continue
            try:
                mod = importlib.import_module(module_name)
            except Exception:
                continue
            if hasattr(mod, "DSDraftExpGen"):
                target_cls = getattr(mod, "DSDraftExpGen")
                target_module = mod
                break

        self.assertIsNotNone(target_cls, "Could not find DSDraftExpGen in rdagent modules")

        # Fake template renderer T and APIBackend for deterministic behavior
        class FakeT:
            def __init__(self, tpl):
                self.tpl = tpl

            def r(self, **kwargs):
                safe_kwargs = {
                    k: (v if isinstance(v, (str, int, float, bool, type(None))) else str(v))
                    for k, v in kwargs.items()
                }
                return f"FAKE_RENDERED:{self.tpl}|{json.dumps(safe_kwargs)}"

        class FakeAPIBackend:
            def build_messages_and_create_chat_completion(self, user_prompt, system_prompt, json_mode, json_target_type):
                # Return a JSON string as the real backend would
                return json.dumps({"description": "generated description", "model_name": "the_model"})

        # Patch at module level used by the class (best-effort)
        try:
            setattr(target_module, "T", FakeT)
        except Exception:
            pass
        try:
            setattr(target_module, "APIBackend", FakeAPIBackend)
        except Exception:
            pass

        # Also patch the function globals to ensure the names used inside the method are replaced
        func = target_cls._init_task_gen
        func.__globals__["T"] = FakeT
        func.__globals__["APIBackend"] = FakeAPIBackend

        # Additionally try to patch the original tpl module if present (defensive)
        try:
            tpl_mod = importlib.import_module("rdagent.utils.agent.tpl")
            setattr(tpl_mod, "T", FakeT)
        except Exception:
            # ignore if module not present or cannot be imported
            pass

        # Instantiate without calling __init__ to avoid constructor requirements
        instance = object.__new__(target_cls)

        # Call the method under test
        resp = instance._init_task_gen(
            targets="Model",
            scenario_desc="some scenario",
            task_output_format="fmt",
            workspace_code=None,
            spec="spec content",
            hypothesis=None,
            exp_and_feedback_desc=None,
            former_task=None,
        )

        # Validate the returned dictionary is what's produced by our FakeAPIBackend
        self.assertIsInstance(resp, dict)
        self.assertEqual(resp.get("model_name"), "the_model")
        self.assertEqual(resp.get("description"), "generated description")
