import pytest
from aider.coders.base_coder import Coder


class DummyModel:
    def __init__(self, tokens, max_input_tokens, name="TestModel"):
        self._tokens = tokens
        # Simulate .info.get("max_input_tokens") behavior via dict
        self.info = {"max_input_tokens": max_input_tokens}
        self.name = name

    def token_count(self, messages):
        # messages is not used in our dummy implementation, keep deterministic
        return self._tokens


class DummyIO:
    def __init__(self, confirm_result=True):
        self.error_msgs = []
        self.outputs = []
        self.last_confirm_msg = None
        self._confirm_result = confirm_result

    def tool_error(self, msg):
        self.error_msgs.append(msg)

    def tool_output(self, msg):
        self.outputs.append(msg)

    def confirm_ask(self, msg):
        # Record prompt and return deterministic configured response
        self.last_confirm_msg = msg
        return self._confirm_result


def _make_dummy_self(tokens, max_input_tokens, confirm_result=True, model_name="TestModel"):
    """Create a minimal 'self' object suitable for calling Coder.check_tokens.

    We intentionally don't instantiate a full Coder to avoid heavy init.
    """
    class DummySelf:
        pass

    ds = DummySelf()
    ds.main_model = DummyModel(tokens, max_input_tokens, name=model_name)
    ds.io = DummyIO(confirm_result=confirm_result)
    return ds


def test_check_tokens_no_limit_round_151():
    """If the model reports no max_input_tokens (0), check_tokens should return True
    and should not call tool_error/tool_output/confirm_ask.
    """
    # max_input_tokens set to 0 -> treated as no limit
    dummy = _make_dummy_self(tokens=500, max_input_tokens=0, confirm_result=False)
    # messages can be any object; token_count ignores it in DummyModel
    res = Coder.check_tokens(dummy, messages=[{"role": "user", "content": "x"}])
    assert res is True
    assert dummy.io.error_msgs == []
    assert dummy.io.outputs == []
    assert dummy.io.last_confirm_msg is None


def test_check_tokens_exceeds_and_decline_round_151():
    """When estimated tokens >= limit and user declines (confirm_ask -> False),
    check_tokens should emit error and guidance outputs and return False.
    """
    tokens = 1000
    dummy = _make_dummy_self(tokens=tokens, max_input_tokens=1000, confirm_result=False, model_name="MyModel")

    res = Coder.check_tokens(dummy, messages=[{"role": "user", "content": "big"}])

    # Should return False because user declined to proceed
    assert res is False

    # One tool_error call with formatted token counts and model name
    assert len(dummy.io.error_msgs) == 1
    err = dummy.io.error_msgs[0]
    # The error message should include the formatted tokens with thousands separator
    assert "1,000" in err
    assert "MyModel" in err
    assert "exceeds" in err

    # Four guidance outputs are expected as per implementation
    assert len(dummy.io.outputs) >= 4
    # Check expected guidance snippets in order
    assert dummy.io.outputs[0] == "To reduce the chat context:"
    assert "Use /drop" in dummy.io.outputs[1]
    assert "Use /clear" in dummy.io.outputs[2]
    assert "Break your code into smaller files" in dummy.io.outputs[3]

    # confirm_ask should have been called with the exact prompt string
    assert dummy.io.last_confirm_msg == "Try to proceed anyway?"


def test_check_tokens_exceeds_and_accept_round_151():
    """When estimated tokens >= limit and user accepts (confirm_ask -> True),
    check_tokens should emit error and guidance outputs and return True.
    """
    tokens = 1234567
    dummy = _make_dummy_self(tokens=tokens, max_input_tokens=1234567, confirm_result=True, model_name="BigModel")

    res = Coder.check_tokens(dummy, messages=[{"role": "user", "content": "huge"}])

    # Since the user accepted, function should return True
    assert res is True

    # Error message should include formatted large number with commas
    assert len(dummy.io.error_msgs) == 1
    assert "1,234,567" in dummy.io.error_msgs[0]
    assert "BigModel" in dummy.io.error_msgs[0]

    # Outputs should be present and match the expected leading guidance
    assert dummy.io.outputs[0] == "To reduce the chat context:"
    assert dummy.io.last_confirm_msg == "Try to proceed anyway?"
