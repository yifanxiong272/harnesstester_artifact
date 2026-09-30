import json
import types
import pytest
import importlib

# Import the module under test
base = importlib.import_module("aider.coders.base_coder")
Coder = base.Coder


class FakeIO:
    def __init__(self):
        self.logged = []
        self.outputs = []

    def log_llm_history(self, tag, content):
        self.logged.append((tag, content))

    def ai_output(self, content):
        self.outputs.append(content)


class FakeHash:
    def __init__(self, val="hash123"):
        self._val = val

    def hexdigest(self):
        return self._val


class CustomLLMException(Exception):
    pass


class FakeModelRaiseContext:
    def send_completion(self, messages, functions, stream, temperature):
        # Always raise an exception instance that should be caught
        raise CustomLLMException("context window exceeded")


class FakeModelRaiseKeyboard:
    def send_completion(self, messages, functions, stream, temperature):
        raise KeyboardInterrupt()


class FakeModelNormal:
    def __init__(self, hash_val=None, completion_obj=None):
        self.received = None
        self.hash_val = hash_val or FakeHash()
        self.completion_obj = completion_obj or {"content": "ok"}

    def send_completion(self, messages, functions, stream, temperature):
        # Record args to ensure signature compatibility
        self.received = (messages, functions, stream, temperature)
        return (self.hash_val, self.completion_obj)


class FakeLiteLLMExceptions:
    """Replacement for module LiteLLMExceptions used by Coder.send().
    exceptions_tuple returns a tuple of exception classes that the except
    clause should catch. get_ex_info returns an object with a .name
    attribute. This fake allows tests to simulate the ContextWindowExceeded
    path by setting the provided name.
    """

    def __init__(self, name_for_get_ex_info=None):
        self._name = name_for_get_ex_info

    def exceptions_tuple(self):
        return (CustomLLMException,)

    def get_ex_info(self, err):
        # Return a simple object with .name attribute to match code usage
        return types.SimpleNamespace(name=self._name)


def make_minimal_coder(io=None):
    # Create a Coder instance without invoking its heavy initializer.
    coder = Coder.__new__(Coder)
    coder.got_reasoning_content = False
    coder.ended_reasoning_content = False
    coder.main_model = None
    coder.partial_response_content = ""
    coder.partial_response_function_call = {}
    coder.io = io or FakeIO()
    coder.stream = False
    coder.temperature = 0.0
    coder.chat_completion_call_hashes = []
    # Provide default stubs that tests can replace or inspect
    coder.calculate_and_show_tokens_and_cost = lambda messages, completion: None
    coder.show_send_output = lambda completion: None
    coder.show_send_output_stream = lambda completion: iter(())
    coder.keyboard_interrupt = lambda: None
    coder.parse_partial_args = lambda: None
    return coder


def test_send_context_window_exception_round_087(monkeypatch):
    io = FakeIO()
    coder = make_minimal_coder(io=io)

    # Replace LiteLLMExceptions in the module so the except clause catches our CustomLLMException
    def fake_lite_factory():
        return FakeLiteLLMExceptions(name_for_get_ex_info="ContextWindowExceededError")

    monkeypatch.setattr(base, "LiteLLMExceptions", lambda: fake_lite_factory())

    # Track whether calculate_and_show_tokens_and_cost was called
    called = []

    def record_calc(messages, completion):
        called.append((messages, completion))

    coder.calculate_and_show_tokens_and_cost = record_calc

    model = FakeModelRaiseContext()

    # Call send: it's a generator function (contains yield in source), so iterate to execute
    gen = coder.send([{"role": "user", "content": "hi"}], model=model)

    with pytest.raises(CustomLLMException):
        list(gen)

    # The ContextWindowExceededError path should still call calculate_and_show_tokens_and_cost
    assert called, "calculate_and_show_tokens_and_cost was not called for ContextWindowExceededError"
    assert called[0][0] == [{"role": "user", "content": "hi"}]
    # completion should be None because send_completion failed
    assert called[0][1] is None

    # Ensure the final log entry for LLM RESPONSE happened (finally block ran)
    assert any(entry[0] == "LLM RESPONSE" for entry in io.logged)


def test_send_keyboard_interrupt_round_087(monkeypatch):
    io = FakeIO()
    coder = make_minimal_coder(io=io)

    # model that raises KeyboardInterrupt
    model = FakeModelRaiseKeyboard()

    # Replace LiteLLMExceptions with a harmless one so KeyboardInterrupt goes to the right except
    monkeypatch.setattr(base, "LiteLLMExceptions", lambda: FakeLiteLLMExceptions(name_for_get_ex_info=None))

    called = {"kb": False}

    def kb_handler():
        called["kb"] = True

    coder.keyboard_interrupt = kb_handler

    gen = coder.send([], model=model)

    with pytest.raises(KeyboardInterrupt):
        list(gen)

    # Ensure keyboard_interrupt handler was invoked
    assert called["kb"] is True

    # Final logging must still have executed
    assert any(tag == "LLM RESPONSE" for (tag, _) in io.logged)


def test_send_function_call_output_round_087():
    io = FakeIO()
    coder = make_minimal_coder(io=io)

    # Normal model that returns a hash and completion object
    fake_hash = FakeHash("hash-xyz")
    model = FakeModelNormal(hash_val=fake_hash, completion_obj={"content": "done"})

    # Ensure LiteLLMExceptions is present but not used in this successful path
    # Patch the module symbol directly
    base.LiteLLMExceptions = lambda: FakeLiteLLMExceptions(name_for_get_ex_info=None)

    # Make show_send_output set partial_response_function_call to non-empty to hit that branch
    def set_partial(completion):
        coder.partial_response_function_call = {"name": "call_me"}

    coder.show_send_output = set_partial

    # parse_partial_args should return a dict so finally block json.dumps is called
    def parse_args():
        return {"arg1": 1}

    coder.parse_partial_args = parse_args

    # Call send and exhaust the generator (will execute try/finally)
    gen = coder.send([{"role": "user", "content": "please call"}], model=model)
    # Should not raise
    list(gen)

    # The model's hexdigest should have been appended
    assert "hash-xyz" in coder.chat_completion_call_hashes

    # Because partial_response_function_call was set and parse_partial_args returned a dict,
    # io.ai_output should have been called with formatted JSON
    expected = json.dumps({"arg1": 1}, indent=4)
    assert expected in io.outputs

    # Final log entry present
    assert any(tag == "LLM RESPONSE" for (tag, _) in io.logged)
