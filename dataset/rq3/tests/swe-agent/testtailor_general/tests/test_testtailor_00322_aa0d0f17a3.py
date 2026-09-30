import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.hooks.open_pr')
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
        """Trigger truncation path when adding the second step (i > 0)."""
        # Construct a small first step and a large second step
        first = {"response": "first response", "observation": "first observation"}
        second = {"response": "second response", "observation": "x" * 500}
        trajectory = [first, second]

        # Recreate prefix/suffix exactly as in the function to compute initial length
        prefix = [
            "<details>",
            "<summary>Thought process ('trajectory') of SWE-agent (click to expand)</summary>",
            "",
            "",
        ]
        prefix_text = "\n".join(prefix)
        suffix = [
            "",
            "</details>",
        ]
        suffix_text = "\n".join(suffix)

        # Build the first step text exactly like the function does to compute its length
        i = 0
        step_strs = [
            f"**🧑‍🚒 Response ({i})**: ",
            f"{first['response'].strip()}",
            f"**👀‍ Observation ({i})**:",
            "```",
            f"{_remove_triple_backticks(first['observation']).strip()}",
            "```",
        ]
        first_step_text = "\n".join(step_strs)

        initial_length = len(prefix_text) + len(suffix_text)

        # Choose char_limit so first step is allowed but second step will exceed the limit.
        # Using +1 ensures first step fits (check is strict >), and any non-empty second step
        # plus the separator will make the next check true.
        char_limit = initial_length + len(first_step_text) + 1

        formatted = format_trajectory_markdown(trajectory, char_limit=char_limit)

        # The formatted result should include the truncation marker appended when i > 0
        self.assertIn("... (truncated due to length limit)", formatted)
