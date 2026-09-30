# file: aider/coders/base_coder.py:1396-1417
# asked: {"lines": [1402, 1403, 1404, 1406, 1407, 1408, 1409, 1410, 1411, 1415, 1416], "branches": [[1401, 1402], [1415, 1416], [1415, 1417]]}
# gained: {"lines": [1402, 1403, 1404, 1406, 1407, 1408, 1409, 1410, 1411, 1415, 1416], "branches": [[1401, 1402], [1415, 1416], [1415, 1417]]}

import pytest

from aider.coders.base_coder import Coder


class FakeMainModel:
    def __init__(self, token_count_value, max_input_tokens, name="fake-model"):
        self._token_count_value = token_count_value
        self.info = {"max_input_tokens": max_input_tokens}
        self.name = name
        self.token_count_called_with = None

    def token_count(self, messages):
        # record the messages passed for inspection and return the preset token count
        self.token_count_called_with = messages
        return self._token_count_value


class FakeIO:
    def __init__(self, confirm_response=True):
        self.error_messages = []
        self.outputs = []
        self.confirm_prompts = []
        self._confirm_response = confirm_response

    def tool_error(self, msg):
        self.error_messages.append(msg)

    def tool_output(self, msg):
        self.outputs.append(msg)

    def confirm_ask(self, prompt):
        self.confirm_prompts.append(prompt)
        return self._confirm_response


def make_fake_self(token_count_value, max_input_tokens, confirm_response=True, name="fake-model"):
    return type("FakeSelf", (), {
        "main_model": FakeMainModel(token_count_value, max_input_tokens, name=name),
        "io": FakeIO(confirm_response),
    })()


def test_check_tokens_below_limit_no_io_calls():
    # Arrange: token count below the model's max_input_tokens should not trigger any IO calls
    fake = make_fake_self(token_count_value=10, max_input_tokens=1000, confirm_response=False)
    messages = [{"role": "user", "content": "hello"}]

    # Act
    result = Coder.check_tokens(fake, messages)

    # Assert
    assert result is True
    assert fake.main_model.token_count_called_with == messages
    # No error or output or confirm prompts should have been recorded
    assert fake.io.error_messages == []
    assert fake.io.outputs == []
    assert fake.io.confirm_prompts == []


def test_check_tokens_exceeds_limit_confirm_false_returns_false_and_outputs():
    # Arrange: token count equals max_input_tokens should trigger the warnings and ask for confirmation.
    fake = make_fake_self(token_count_value=1000, max_input_tokens=1000, confirm_response=False, name="big-model")
    messages = ["dummy"]

    # Act
    result = Coder.check_tokens(fake, messages)

    # Assert: function should return False because confirm_ask returned False
    assert result is False

    # tool_error should have been called once and include model name and the token numbers
    assert len(fake.io.error_messages) == 1
    err = fake.io.error_messages[0]
    assert "big-model" in err
    assert "token" in err.lower()
    # numbers formatted with commas for large numbers are OK; at least ensure the count appears
    assert "1,000" in err or "1000" in err

    # There should be five tool_output calls as per the implementation guidance messages
    assert len(fake.io.outputs) == 5
    assert any("To reduce the chat context" in o for o in fake.io.outputs)
    assert any("- Use /drop" in o for o in fake.io.outputs)
    assert any("- Use /clear" in o for o in fake.io.outputs)
    assert any("- Break your code into smaller files" in o for o in fake.io.outputs)
    assert any("It's probably safe to try and send the request" in o for o in fake.io.outputs)

    # confirm_ask should have been called exactly once with the expected prompt
    assert len(fake.io.confirm_prompts) == 1
    assert "Try to proceed anyway?" in fake.io.confirm_prompts[0]


def test_check_tokens_exceeds_limit_confirm_true_returns_true_but_outputs_present():
    # Arrange: when user confirms (confirm_ask returns True), function should return True
    fake = make_fake_self(token_count_value=2000, max_input_tokens=1000, confirm_response=True, name="giant-model")
    messages = ["x"]

    # Act
    result = Coder.check_tokens(fake, messages)

    # Assert: because confirm_ask returned True, the function should return True
    assert result is True

    # The same error and outputs should have been produced
    assert len(fake.io.error_messages) == 1
    assert "giant-model" in fake.io.error_messages[0]
    assert len(fake.io.outputs) == 5

    # confirm_ask should have been called and returned True (we recorded the prompt)
    assert len(fake.io.confirm_prompts) == 1
    assert "Try to proceed anyway?" in fake.io.confirm_prompts[0]
