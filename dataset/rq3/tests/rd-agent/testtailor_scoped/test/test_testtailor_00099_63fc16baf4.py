import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.data_science.share.notebook')
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
        # Ensure NotebookConverter will call the LLM path when a Task is provided.
        converter = NotebookConverter()
        task = Task(name="demo_task", description="A demo task for notebook intro generation")

        # Minimal code containing a main function and a section divider print.
        code = """def helper():
    pass

def main():
    print("Section: Intro")
    # Example comment under section
    helper()

if __name__ == "__main__":
    main()
"""
        stdout = "Section: Intro\n"

        # Patch the template loader T and the API backend used to generate the intro content.
        module_path = "rdagent.components.coder.data_science.share.notebook"
        with unittest.mock.patch(f"{module_path}.T") as mockT, unittest.mock.patch(
            f"{module_path}.APIBackend"
        ) as mockAPI:
            # Make T(...) return an object with an r() method that returns a simple string.
            def T_side(key):
                class Dummy:
                    def __init__(self, k):
                        self.k = k

                    def r(self, **kwargs):
                        return f"template:{self.k}"

                return Dummy(key)

            mockT.side_effect = T_side

            # Make the API backend return a response that matches MarkdownAgentOut's expected fenced block.
            api_inst = mockAPI.return_value
            api_inst.build_messages_and_create_chat_completion.return_value = (
                "prefix ````markdown\nGenerated Intro Content\n```` suffix"
            )

            # Run conversion
            nb_str = converter.convert(task=task, code=code, stdout=stdout)

        # The converter should include a markdown cell with the extracted intro content.
        self.assertIsInstance(nb_str, str)
        self.assertIn('"cell_type": "markdown"', nb_str)
        self.assertIn("Generated Intro Content", nb_str)
