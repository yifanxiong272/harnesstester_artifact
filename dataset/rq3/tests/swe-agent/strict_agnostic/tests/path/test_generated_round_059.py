import pytest

from sweagent.run.hooks.abstract import CombinedRunHooks


class _FakeHook:
    """Simple local fake hook to observe which methods are called and with what args.

    Deterministic and side-effect free.
    """

    def __init__(self):
        self.calls = []

    def on_init(self, *, run):
        self.calls.append(("on_init", run))

    def on_start(self):
        self.calls.append(("on_start", None))

    def on_end(self):
        self.calls.append(("on_end", None))

    def on_instance_start(self, *, index, env, problem_statement):
        self.calls.append(("on_instance_start", index, env, problem_statement))

    def on_instance_skipped(self):
        self.calls.append(("on_instance_skipped", None))

    def on_instance_completed(self, *, result):
        self.calls.append(("on_instance_completed", result))


def test_hooks_property_and_on_init_round_059():
    """Verify that hooks property starts empty and on_init forwards to added hooks.

    This covers the property return (line 41) and the on_init loop & call (lines 44-45).
    """
    crh = CombinedRunHooks()

    # initially no hooks
    assert crh.hooks == []

    # add a fake hook and ensure it receives on_init
    fh = _FakeHook()
    crh.add_hook(fh)
    assert len(crh.hooks) == 1 and crh.hooks[0] is fh

    sentinel = object()
    # on_init should forward the run argument to the hook
    ret = crh.on_init(run=sentinel)
    assert ret is None
    assert fh.calls == [("on_init", sentinel)]


def test_on_instance_skipped_round_059():
    """Verify that on_instance_skipped forwards the call to each hook.

    Covers the on_instance_skipped loop and inner call (lines 62-63).
    """
    crh = CombinedRunHooks()
    fh1 = _FakeHook()
    fh2 = _FakeHook()
    crh.add_hook(fh1)
    crh.add_hook(fh2)

    ret = crh.on_instance_skipped()
    assert ret is None

    # both hooks must have received the skipped notification
    assert fh1.calls == [("on_instance_skipped", None)]
    assert fh2.calls == [("on_instance_skipped", None)]


def test_methods_no_hooks_do_not_error_round_059():
    """Calling various CombinedRunHooks methods with no hooks should be a no-op and not raise.

    This exercises the empty-loop branches (44->-43 and 62->-61) for on_init and
    on_instance_skipped respectively, and also checks other method no-op behavior.
    """
    crh = CombinedRunHooks()

    # With no hooks present these calls should be safe and return None
    assert crh.on_init(run="any") is None
    assert crh.on_start() is None
    assert crh.on_end() is None
    assert crh.on_instance_skipped() is None
    assert crh.on_instance_start(index=0, env=None, problem_statement=None) is None
    assert crh.on_instance_completed(result=None) is None
