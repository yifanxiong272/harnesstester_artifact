import builtins
import types
from sweagent.agent.action_sampler import BinaryTrajectoryComparison


class LoggerStub:
    def __init__(self):
        self.calls = []

    def debug(self, *args, **kwargs):
        # record raw args for assertion; do not format
        self.calls.append((args, kwargs))


class ToolsStub:
    def __init__(self, mapping=None):
        # mapping: a callable or dict to produce (thought, action) from a completion
        self.mapping = mapping
        self.calls = []

    def parse_actions(self, pc):
        # record call
        self.calls.append(pc)
        if callable(self.mapping):
            return self.mapping(pc)
        if isinstance(self.mapping, dict):
            key = pc.get("id")
            return self.mapping.get(key, (f"thought-{key}", f"action-{key}"))
        # default behavior: return tuple based on pc content
        key = pc.get("id") if isinstance(pc, dict) else str(pc)
        return (f"thought-{key}", f"action-{key}")


def _make_btc_with_tools(tools):
    """Create a BinaryTrajectoryComparison instance without calling its __init__.
    We set only the attributes needed by filter_duplicates: _tools and _logger.
    """
    inst = object.__new__(BinaryTrajectoryComparison)
    inst._tools = tools
    inst._logger = LoggerStub()
    return inst


def test_no_duplicates_round_027():
    # Tools returns unique actions per completion, so nothing is filtered.
    tools = ToolsStub(mapping=lambda pc: (f"thought-{pc.get('id')}", f"action-{pc.get('id')}"))
    btc = _make_btc_with_tools(tools)

    completions = [{"id": 1, "payload": "a"}, {"id": 2, "payload": "b"}]
    out = btc.filter_duplicates(completions)

    # Should return the same sequence (no duplicates removed)
    assert out == completions
    # parse_actions should have been called once per completion, in order
    assert len(tools.calls) == 2
    assert tools.calls[0] == completions[0]
    assert tools.calls[1] == completions[1]
    # No logging should occur because nothing was filtered
    assert btc._logger.calls == []


def test_with_duplicates_round_027():
    # Tools returns the same action for completions with the same 'id'
    tools = ToolsStub()
    btc = _make_btc_with_tools(tools)

    # Two completions share id=1 -> same action; one unique completion id=2
    c1 = {"id": 1, "text": "first"}
    c2 = {"id": 1, "text": "second"}  # duplicate action by design
    c3 = {"id": 2, "text": "third"}
    completions = [c1, c2, c3]

    out = btc.filter_duplicates(completions)

    # Expect only the first of the duplicate ids preserved and the unique one
    assert out == [c1, c3]

    # parse_actions should have been called for each input
    assert len(tools.calls) == 3
    assert tools.calls[0] is c1
    assert tools.calls[1] is c2
    assert tools.calls[2] is c3

    # Logging should have been called once indicating reduction 3 -> 2
    assert len(btc._logger.calls) == 1
    (args, kwargs) = btc._logger.calls[0]
    # logger.debug called with format string and two integers: original len and filtered len
    assert isinstance(args[0], str) and "Filtering duplicates" in args[0]
    assert args[1] == 3
    assert args[2] == 2
    assert kwargs == {}
