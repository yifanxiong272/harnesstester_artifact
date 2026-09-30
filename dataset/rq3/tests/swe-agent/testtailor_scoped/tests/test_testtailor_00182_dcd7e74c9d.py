import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.action_sampler')
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
        """complete the test case here"""
        # Minimal config with templates that will be processed by jinja2.Template inside the code under test
        class Config:
            system_template = "SYSTEM_TEMPLATE"
            instance_template = "Problem: {{problem_statement}}\nExtra: {{extra}}\nTrajectory:\n{{traj}}"
            comparison_template = (
                "Compare:\n"
                "Thought1: {{thought1}}\nAction1: {{action1}}\n"
                "Thought2: {{thought2}}\nAction2: {{action2}}"
            )

        # Minimal problem statement implementation satisfying the Protocol
        class ProblemStatementImpl:
            def get_problem_statement(self) -> str:
                return "Solve this problem"

            def get_extra_fields(self) -> dict:
                return {"extra": "EXTRA_FIELD"}

        # Simple logger to capture debug calls (not strictly required but prevents missing attribute errors)
        class DummyLogger:
            def __init__(self):
                self.debug_calls = []
                self.info_calls = []
                self.warning_calls = []

            def debug(self, *args, **kwargs):
                self.debug_calls.append((args, kwargs))

            def info(self, *args, **kwargs):
                self.info_calls.append((args, kwargs))

            def warning(self, *args, **kwargs):
                self.warning_calls.append((args, kwargs))

        # Create instance of the class under test
        config = Config()
        # model and tools are not used by format_messages, so pass simple objects
        model = object()
        tools = object()
        btc = BinaryTrajectoryComparison(config, model, tools)
        # Override logger to avoid relying on external setup
        btc._logger = DummyLogger()

        # Prepare a trajectory matching the expected format: list of dicts with 'action' and 'observation'
        trajectory = [
            {"action": "a1", "observation": "o1"},
            {"action": "a2", "observation": "o2"},
        ]

        problem = ProblemStatementImpl()

        # Call format_messages without cache control
        msgs = btc.format_messages(
            problem_statement=problem,
            trajectory=trajectory,
            thought1="T1",
            action1="ACT1",
            thought2="T2",
            action2="ACT2",
            use_cache_control=False,
        )

        # Validate basic structure
        self.assertIsInstance(msgs, list)
        self.assertEqual(len(msgs), 3)

        # First message is system message
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[0]["content"], config.system_template)

        # Second message is the rendered instance (user) message without cache control
        self.assertEqual(msgs[1]["role"], "user")
        self.assertIsInstance(msgs[1]["content"], list)
        self.assertEqual(len(msgs[1]["content"]), 1)
        inst_part = msgs[1]["content"][0]
        self.assertEqual(inst_part["type"], "text")
        # Build expected trajectory rendering to compare
        expected_traj = (
            "Action 0: a1\n Observation 0: o1\n"
            "Action 1: a2\n Observation 1: o2"
        )
        expected_instance_text = f"Problem: {problem.get_problem_statement()}\nExtra: EXTRA_FIELD\nTrajectory:\n{expected_traj}"
        self.assertEqual(inst_part["text"], expected_instance_text)
        # Should not contain cache_control key when use_cache_control=False
        self.assertNotIn("cache_control", inst_part)

        # Third message is the comparison message
        self.assertEqual(msgs[2]["role"], "user")
        self.assertIsInstance(msgs[2]["content"], list)
        self.assertEqual(len(msgs[2]["content"]), 1)
        comp_part = msgs[2]["content"][0]
        self.assertEqual(comp_part["type"], "text")
        expected_comp_text = (
            "Compare:\n"
            "Thought1: T1\nAction1: ACT1\n"
            "Thought2: T2\nAction2: ACT2"
        )
        self.assertEqual(comp_part["text"], expected_comp_text)

        # Now call with cache control enabled and ensure the ephemeral flag is present on the instance message
        msgs_cc = btc.format_messages(
            problem_statement=problem,
            trajectory=trajectory,
            thought1="T1",
            action1="ACT1",
            thought2="T2",
            action2="ACT2",
            use_cache_control=True,
        )
        inst_part_cc = msgs_cc[1]["content"][0]
        self.assertIn("cache_control", inst_part_cc)
        self.assertEqual(inst_part_cc["cache_control"], {"type": "ephemeral"})
