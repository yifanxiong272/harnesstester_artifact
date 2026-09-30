import pytest
from aider import commands


class DummyCoder:
    def __init__(self):
        self.events = []

    def event(self, name):
        # deterministic side effect
        self.events.append(name)


class DummyIO:
    def __init__(self):
        self.errors = []

    def tool_error(self, msg):
        # deterministic side effect
        self.errors.append(msg)


def make_commands_instance():
    # Avoid running Commands.__init__ (complex environment). Create instance
    # and attach only the attributes used by Commands.run.
    inst = object.__new__(commands.Commands)
    inst.coder = DummyCoder()
    inst.io = DummyIO()
    return inst


def test_bang_prefix_round_101():
    cmd = make_commands_instance()

    # record calls to do_run via a deterministic stub
    calls = []

    def fake_do_run(name, args):
        calls.append((name, args))
        return f"done:{name}:{args}"

    cmd.do_run = fake_do_run

    # Input starting with '!'
    result = cmd.run("!runme-now")

    # coder.event should be called with 'command_run' and do_run should be invoked
    assert cmd.coder.events == ["command_run"]
    assert calls == [("run", "runme-now")]
    assert result == "done:run:runme-now"


def test_matching_none_round_101():
    cmd = make_commands_instance()

    # matching_commands returns None -> run should return None and do nothing
    cmd.matching_commands = lambda inp: None

    result = cmd.run("/anything")

    assert result is None
    assert cmd.coder.events == []
    assert cmd.io.errors == []


def test_single_matching_command_round_101():
    cmd = make_commands_instance()

    # single matching command: matching_commands -> (list_of_matches, first_word, rest)
    cmd.matching_commands = lambda inp: (["/echo"], "/echo", "hello world")

    called = {}

    def fake_do_run(name, rest):
        # return tuple so assertions can inspect it
        called['args'] = (name, rest)
        return ("ran", name, rest)

    cmd.do_run = fake_do_run

    result = cmd.run("/echo hello world")

    # coder.event should be called with derived command name (without leading '/').
    assert cmd.coder.events == ["command_echo"]
    assert called['args'] == ("echo", "hello world")
    assert result == ("ran", "echo", "hello world")


def test_first_word_in_matching_commands_round_101():
    cmd = make_commands_instance()

    # multiple matches but first_word is one of them -> should pick first_word
    cmd.matching_commands = lambda inp: (["/a", "/b"], "/a", "rest-of-input")

    def fake_do_run(name, rest):
        return f"did:{name}:{rest}"

    cmd.do_run = fake_do_run

    result = cmd.run("/a rest-of-input")

    assert cmd.coder.events == ["command_a"]
    assert result == "did:a:rest-of-input"


def test_ambiguous_and_invalid_round_101():
    # Ambiguous branch: len(matching_commands) > 1 and first_word not in matching_commands
    cmd1 = make_commands_instance()
    cmd1.matching_commands = lambda inp: (["/one", "/two"], "/three", "x")

    # If do_run were called erroneously the test would fail; ensure it raises if invoked
    def should_not_run(*_):
        raise AssertionError("do_run should not be called for ambiguous/invalid commands")

    cmd1.do_run = should_not_run

    cmd1.run("/three x")

    assert cmd1.io.errors == ["Ambiguous command: /one, /two"]

    # Invalid branch: empty matching_commands -> should report invalid command using first_word
    cmd2 = make_commands_instance()
    cmd2.matching_commands = lambda inp: ([], "/nada", "")
    cmd2.do_run = should_not_run

    cmd2.run("/nada")

    assert cmd2.io.errors == ["Invalid command: /nada"]
