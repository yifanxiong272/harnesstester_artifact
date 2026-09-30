# file: sweagent/tools/parsing.py:52-66
# asked: {"lines": [62], "branches": []}
# gained: {"lines": [62], "branches": []}

import textwrap
import pytest
from sweagent.tools.parsing import AbstractParseFunction


def test_call_raises_not_implemented():
    """
    Create a concrete subclass that intentionally delegates to the abstract
    base implementation of __call__ (which should raise NotImplementedError).
    This ensures the base-class raise path is executed.
    """

    class CallsSuper(AbstractParseFunction):
        # Implement __call__ but call super().__call__ to trigger the NotImplementedError
        def __call__(self, model_response, commands: list, strict=False):
            # delegate to base implementation that should raise
            return super().__call__(model_response, commands, strict=strict)

    inst = CallsSuper()
    # Call with arbitrary arguments; the base class should raise NotImplementedError
    with pytest.raises(NotImplementedError):
        inst("some response", [], strict=True)


def test_format_error_template_dedent():
    """
    Verify that the format_error_template property returns a dedented version
    of the error_message string.
    """

    class HasErrorMessage(AbstractParseFunction):
        # Provide an implementation so class is concrete
        error_message = """
            Error occurred:
                - reason: something went wrong
                - code: 123
            End of message.
        """

        def __call__(self, model_response, commands: list, strict=False):
            # simple concrete implementation that would not be used in this test
            return ("ok", "ok")

    inst = HasErrorMessage()
    # The property should dedent the multi-line message
    formatted = inst.format_error_template

    # Build the expected dedented string using textwrap.dedent to mirror implementation
    expected = textwrap.dedent(HasErrorMessage.error_message)
    assert formatted == expected

    # Ensure the first non-empty line has no leading indentation
    lines = formatted.splitlines()
    # find first non-empty line
    first_non_empty = next((ln for ln in lines if ln.strip() != ""), "")
    assert first_non_empty == "Error occurred:"

    # Ensure that content lines are present
    assert "Error occurred:" in formatted
    assert "- reason: something went wrong" in formatted
    assert "End of message." in formatted
