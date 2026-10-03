from unittest.mock import Mock

from pydantic import SecretStr

import openhands.sdk.llm.llm as llm_mod
from openhands.sdk.llm import LLM


def test_probe_001(monkeypatch):
    """Probe that a ResponseCompletedEvent yielded during stream iteration
    is delivered to _finalize_stream_response (not overwritten by ret.completed_response).

    Activation: patch litellm_responses to return an iterable with
    completed_response = None but that yields a ResponseCompletedEvent-like sentinel.
    """

    # Prevent any network during LLM construction
    monkeypatch.setattr(
        "openhands.sdk.llm.utils.model_info.httpx.get",
        lambda *a, **k: Mock(json=lambda: {"data": []}),
    )

    # Replace the module's ResponseCompletedEvent with a simple sentinel class
    class _SentinelResponseCompletedEvent:
        """Lightweight sentinel used only for isinstance checks in the target code.
        This avoids attempting to construct the real pydantic model which requires
        structured fields and caused ValidationError in the original probe.
        """
        pass

    monkeypatch.setattr(llm_mod, "ResponseCompletedEvent", _SentinelResponseCompletedEvent)

    # Create the event instance that the stream will yield
    event_instance = _SentinelResponseCompletedEvent()

    # Build a custom iterable that yields the event and declares completed_response = None
    class DummyStream:
        completed_response = None

        def __init__(self, event):
            self._event = event
            self._yielded = False

        def __iter__(self):
            return self

        def __next__(self):
            if not self._yielded:
                self._yielded = True
                return self._event
            raise StopIteration

    # Patch the litellm_responses symbol in the target module to return our DummyStream
    def fake_litellm_responses(**kwargs):
        return DummyStream(event_instance)

    monkeypatch.setattr(llm_mod, "litellm_responses", fake_litellm_responses)

    # Create an LLM instance deterministically and avoid retries
    llm = LLM(model="gpt-4o", api_key=SecretStr("test-key"), usage_id="probe", num_retries=0)

    # To avoid the real _process_stream_event depending on event internals,
    # replace the instance method with a deterministic stub that returns (None, None).
    # Assigning at the instance level so other tests are not affected.
    llm._process_stream_event = lambda event, emit_deltas=None: (None, None)

    # Capture calls to _finalize_stream_response
    captured = {}

    def fake_finalize(completed_response, collected_output_items):
        captured["args"] = (completed_response, collected_output_items)
        return "FINALIZED"

    # Monkeypatch the instance method
    setattr(llm, "_finalize_stream_response", fake_finalize)

    # Invoke the public entrypoint with stream=True. Use empty messages to keep inputs minimal.
    result = llm.responses(messages=[], stream=True)

    # Ensure finalizer was invoked and captured its arguments
    assert "args" in captured, "_finalize_stream_response was not called"

    finalized_completed_response, finalized_collected = captured["args"]

    # Primary oracle: the completed_response given to the finalizer must be the event yielded during iteration
    assert finalized_completed_response is event_instance, (
        "Expected the yielded ResponseCompletedEvent-like sentinel to be forwarded to _finalize_stream_response; "
        "if this assertion fails, the module may be overwriting the discovered event with ret.completed_response."
    )

    # Supporting check: collected_output_items must be a list (could be empty)
    assert isinstance(finalized_collected, list), "collected_output_items should be a list"

    # The public call should return whatever our fake finalizer returned
    assert result == "FINALIZED"
