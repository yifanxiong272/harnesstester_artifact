from browser_use.agent.views import AgentHistory, HistoryTreeProcessor


def test_probe_001_zero_index_is_valid_key_and_converted():
    """Probe: index==0 must be treated as a valid key (not falsy) and converted.

    We create a minimal model_output-like object with one action whose get_index() -> 0.
    We provide a selector_map with key 0 mapped to a simple sentinel object. To avoid
    depending on the concrete DOMElementNode constructor signature, we patch
    HistoryTreeProcessor.convert_dom_element_to_history_element to return a
    deterministic sentinel value ('CONVERTED'). The primary oracle asserts that the
    result at position 0 equals that sentinel (not None).
    """

    class DummyAction:
        def get_index(self):
            return 0

    class DummyModelOutput:
        def __init__(self, actions):
            # AgentHistory.get_interacted_element iterates `model_output.action`
            self.action = actions

    model_output = DummyModelOutput([DummyAction()])
    selector_map = {0: object()}  # presence of key 0 should be honored by function

    # Patch the converter to a deterministic sentinel so we don't depend on DOMElementNode/DOMHistoryElement constructors.
    original_converter = getattr(HistoryTreeProcessor, "convert_dom_element_to_history_element")
    try:
        setattr(HistoryTreeProcessor, "convert_dom_element_to_history_element", staticmethod(lambda el: "CONVERTED"))
        result = AgentHistory.get_interacted_element(model_output, selector_map)
    finally:
        # restore original to avoid affecting other tests
        setattr(HistoryTreeProcessor, "convert_dom_element_to_history_element", original_converter)

    assert isinstance(result, list), "Expected a list result"
    # PRIMARY ORACLE: index 0 must be converted and returned (not None). This will fail on the buggy implementation
    # that uses `if index and index in selector_map:` which treats 0 as falsy.
    assert result[0] == "CONVERTED", (
        "When an action index is 0 and selector_map contains 0, get_interacted_element should return the converted "
        "DOMHistoryElement at that position (0 is a valid index key)."
    )
