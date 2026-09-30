from sweagent.run.hooks.abstract import CombinedRunHooks


class DummyHook:
    """Lightweight in-memory hook that records calls for assertions."""

    def __init__(self, name: str):
        self.name = name
        self.calls = []

    def on_init(self, *, run):
        # record the named param to assert it's passed through correctly
        self.calls.append(("on_init", run))

    def on_start(self):
        self.calls.append(("on_start", None))

    def on_end(self):
        self.calls.append(("on_end", None))

    def on_instance_start(self, *, index, env, problem_statement):
        # record multiple args to ensure they're forwarded
        self.calls.append(("on_instance_start", index, env, problem_statement))

    def on_instance_skipped(self):
        self.calls.append(("on_instance_skipped", None))

    def on_instance_completed(self, *, result):
        self.calls.append(("on_instance_completed", result))


def test_hooks_property_round_057():
    crh = CombinedRunHooks()

    # Initially should expose the internal list (empty)
    assert isinstance(crh.hooks, list)
    assert crh.hooks == []

    # After adding, the same object should be present via the property
    h = DummyHook("h1")
    crh.add_hook(h)
    assert crh.hooks[-1] is h


def test_on_init_and_skipped_round_057():
    crh = CombinedRunHooks()
    a = DummyHook("a")
    b = DummyHook("b")
    crh.add_hook(a)
    crh.add_hook(b)

    # on_init should call each hook.on_init with the named parameter 'run'
    crh.on_init(run="RUN_X")
    assert a.calls == [("on_init", "RUN_X")]
    assert b.calls == [("on_init", "RUN_X")]

    # on_instance_skipped should call each hook.on_instance_skipped
    crh.on_instance_skipped()
    assert a.calls[-1] == ("on_instance_skipped", None)
    assert b.calls[-1] == ("on_instance_skipped", None)


def test_other_events_forwarded_round_057():
    crh = CombinedRunHooks()
    h = DummyHook("single")
    crh.add_hook(h)

    # on_start and on_end forwarding
    crh.on_start()
    crh.on_end()
    assert ("on_start", None) in h.calls
    assert ("on_end", None) in h.calls

    # on_instance_start should forward index, env, and problem_statement
    crh.on_instance_start(index=7, env="ENV_OBJ", problem_statement="PS_CFG")
    assert ("on_instance_start", 7, "ENV_OBJ", "PS_CFG") in h.calls

    # on_instance_completed should forward result
    crh.on_instance_completed(result="FINAL_RESULT")
    assert ("on_instance_completed", "FINAL_RESULT") in h.calls
