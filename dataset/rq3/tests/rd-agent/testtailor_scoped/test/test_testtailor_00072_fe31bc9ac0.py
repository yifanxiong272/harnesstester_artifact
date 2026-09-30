import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.app.qlib_rd_loop.factor_from_report')
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
        """Find and invoke the project's generate_hypothesis function while mocking T and APIBackend."""
        # Local imports inside the test to avoid top-level import requirements
        import importlib
        import json
        import os
        from pathlib import Path
        from unittest.mock import patch

        # Prepare inputs
        factor_result = {"factor1": {"score": 0.9, "desc": "important"}}
        report_content = "This is a short report content used for testing."

        # The JSON we expect the (mocked) API to return
        expected_response = {
            "hypothesis": "Test hypothesis",
            "reason": "Because factor1 is highly important given the report content.",
            "concise_reason": "factor1 important",
            "concise_observation": "report mentions high relevance",
            "concise_justification": "strong correlation",
            "concise_knowledge": "domain knowledge supports link",
        }

        # Locate the repository root (the directory that contains the 'rdagent' package)
        current = Path(__file__).resolve().parent
        repo_root = current
        while repo_root != repo_root.parent and not (repo_root / "rdagent").exists():
            repo_root = repo_root.parent
        self.assertTrue((repo_root / "rdagent").exists(), "Could not find 'rdagent' package in repo tree")

        # Search for the module that defines generate_hypothesis
        target_file = None
        for p in (repo_root / "rdagent").rglob("*.py"):
            try:
                text = p.read_text(encoding="utf-8")
            except Exception:
                continue
            if "def generate_hypothesis(" in text:
                target_file = p
                break

        self.assertIsNotNone(target_file, "Could not find a file defining generate_hypothesis in rdagent package")

        # Compute module name and import it
        rel = target_file.relative_to(repo_root).with_suffix("")
        module_name = ".".join(rel.parts)
        module = importlib.import_module(module_name)

        # Ensure the function exists on the module
        func = getattr(module, "generate_hypothesis", None)
        self.assertIsNotNone(func, f"Module {module_name} does not expose generate_hypothesis")

        # Patch the template loader T and the APIBackend used inside the found module.
        # Use create=True so attributes are created if they don't exist on the module.
        with patch.object(module, "T", create=True) as mock_T, patch.object(
            module, "APIBackend", create=True
        ) as mock_APIBackend:
            # Configure T().r() to return different strings for system and user prompts
            mock_T.return_value.r.side_effect = ["system-prompt-text", "user-prompt-text"]

            # Configure APIBackend().build_messages_and_create_chat_completion to return JSON string
            mock_api_instance = mock_APIBackend.return_value
            mock_api_instance.build_messages_and_create_chat_completion.return_value = json.dumps(
                expected_response
            )

            # Call the function under test
            result = func(factor_result, report_content)

            # Verify result type and fields
            self.assertIsNotNone(result)
            self.assertEqual(result.hypothesis, expected_response["hypothesis"])
            self.assertEqual(result.reason, expected_response["reason"])
            self.assertEqual(result.concise_reason, expected_response["concise_reason"])
            self.assertEqual(result.concise_observation, expected_response["concise_observation"])
            self.assertEqual(result.concise_justification, expected_response["concise_justification"])
            self.assertEqual(result.concise_knowledge, expected_response["concise_knowledge"])

            # Verify T was called for both system and user prompts (at least twice)
            calls = [c[0][0] for c in mock_T.call_args_list] if mock_T.call_args_list else []
            self.assertTrue(len(calls) >= 2, "Expected T to be called at least twice for system and user prompts")
            self.assertIn(".prompts:hypothesis_generation.system", calls[0])
            self.assertIn(".prompts:hypothesis_generation.user", calls[1])

            # Verify the API backend was invoked
            mock_api_instance.build_messages_and_create_chat_completion.assert_called_once()
