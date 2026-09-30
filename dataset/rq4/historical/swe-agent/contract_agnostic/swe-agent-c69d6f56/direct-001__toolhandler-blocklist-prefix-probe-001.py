from sweagent.tools.tools import ToolHandler


class FakeFilter:
    def __init__(self):
        # blocklist contains the prefix that should match the start of the action
        self.blocklist = ["su"]
        self.blocklist_standalone = []
        self.block_unless_regex = {}


class FakeConfig:
    def __init__(self):
        self.filter = FakeFilter()


class FakeSelf:
    def __init__(self):
        self.config = FakeConfig()


def test_probe_001_should_block_action_for_prefix():
    """Probe whether a blocklist entry that is a prefix ("su") blocks action 'su root'.

    This exercises the public entrypoint ToolHandler.should_block_action as an
    unbound method, providing a minimal fake `self` with deterministic filter
    settings. The independent invariant: if a blocklist contains a prefix b and
    action.startswith(b) then the action should be blocked.
    """
    fake_self = FakeSelf()
    result = ToolHandler.should_block_action(fake_self, "su root")
    # Primary behavioral oracle: the action starting with 'su' must be blocked.
    assert result is True, f"Expected 'su root' to be blocked when blocklist contains 'su', got {result}"
