from browser_use.agent import views
from browser_use.agent.views import AgentHistory


def test_probe_001():
    # Deterministic fake actions and model output
    class FakeAction:
        def __init__(self, idx):
            self._idx = idx

        def get_index(self):
            return self._idx

    class FakeModelOutput:
        def __init__(self, actions):
            self.action = actions

    dom0 = object()
    dom1 = object()

    model_output = FakeModelOutput([FakeAction(0), FakeAction(1)])
    selector_map = {0: dom0, 1: dom1}

    # Monkeypatch the HistoryTreeProcessor conversion to return deterministic sentinels
    processor = views.HistoryTreeProcessor
    orig = processor.convert_dom_element_to_history_element
    try:
        def _convert(el):
            if el is dom0:
                return "SENTINEL_DOM0"
            if el is dom1:
                return "SENTINEL_DOM1"
            return "UNKNOWN"

        # Preserve staticmethod/descriptor behavior by installing as a plain attribute
        processor.convert_dom_element_to_history_element = staticmethod(_convert)

        # Call the target entrypoint
        result = AgentHistory.get_interacted_element(model_output, selector_map)
    finally:
        # Restore original to avoid test pollution
        processor.convert_dom_element_to_history_element = orig

    # Observable checks (primary oracle is the first assertion)
    assert isinstance(result, list)
    assert len(result) == 2
    # Primary behavioral oracle: index 0 present in selector_map must be converted, not treated as falsy
    assert result[0] == "SENTINEL_DOM0"
    # Also verify the other element converted as expected
    assert result[1] == "SENTINEL_DOM1"
