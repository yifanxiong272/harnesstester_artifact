from sweagent.tools.tools import ToolHandler


def test_probe_001_should_block_prefix_blocklist():
    """Verify that a blocklist entry that is a prefix (e.g. 'vim') blocks an action with arguments (e.g. 'vim -h').

    We avoid calling ToolHandler.__init__ by creating the instance with object.__new__
    and injecting a minimal config.filter structure the method reads. This keeps the
    test deterministic and focused on the single public entrypoint should_block_action.
    """

    # Construct a ToolHandler instance without running its constructor
    th = object.__new__(ToolHandler)

    # Minimal filter/config objects matching attributes accessed by should_block_action
    class _Filter:
        def __init__(self):
            # Activation condition: blocklist contains 'vim'
            self.blocklist = ["vim"]
            # No standalone full-action matches
            self.blocklist_standalone = []
            # No regex exceptions
            self.block_unless_regex = {}

    class _Config:
        def __init__(self):
            self.filter = _Filter()

    th.config = _Config()

    # Primary observable oracle: the method should consider 'vim -h' blocked
    assert th.should_block_action("vim -h") is True
