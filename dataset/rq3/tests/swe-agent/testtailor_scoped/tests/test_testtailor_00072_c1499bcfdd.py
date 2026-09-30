import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.run_single')
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
        """Verify RunSingleConfig._get_auto_correct returns the expected suggestions."""
        autos = RunSingleConfig._get_auto_correct()
        self.assertEqual(len(autos), 9)

        expected = [
            ("model", "agent.model.name", None),
            ("agent.model", "agent.model.name", None),
            ("model.name", "agent.model.name", None),
            ("per_instance_cost_limit", "agent.model.per_instance_cost_limit", None),
            ("model.per_instance_cost_limit", "agent.model.per_instance_cost_limit", None),
            ("config_file", "config", None),
            (
                "data_path",
                "",
                "--data_path is no longer support for SWE-A 1.0. Please check the tutorial and use one of the --problem_statement options, e.g., --problem_statement.github_url or --problem_statement.path",
            ),
            (
                "repo_path",
                "",
                "--repo_path is no longer support for SWE-A 1.0. Please check the tutorial and use one of the --env.repo options, e.g., --env.repo.github_url or --env.repo.path",
            ),
            ("repo.path", "env.repo.path", None),
        ]

        for idx, (orig, alt, help_text) in enumerate(expected):
            item = autos[idx]
            self.assertEqual(item.original, orig, msg=f"mismatch original at index {idx}")
            self.assertEqual(item.alternative, alt, msg=f"mismatch alternative at index {idx}")
            self.assertEqual(item.help, help_text, msg=f"mismatch help at index {idx}")
