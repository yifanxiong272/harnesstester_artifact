import types

import aider.io as io_mod
from aider.io import AutoCompleter


# Stand-in for prompt_toolkit.completion.Completion to avoid external dependency
class SimpleCompletion:
    def __init__(self, text, start_position=0):
        self.text = text
        self.start_position = start_position


class DummyCommands:
    def __init__(self, matching_return, raw_map=None, completions_map=None, commands_list=None):
        # matching_return should be a tuple (matches, _, _)
        self._matching_return = matching_return
        self.raw_map = raw_map or {}
        self.completions_map = completions_map or {}
        self.get_completions_called = 0
        # Optional explicit list to return from get_commands
        self._commands_list = commands_list

    def matching_commands(self, cmd):
        return self._matching_return

    def get_raw_completions(self, cmd):
        return self.raw_map.get(cmd)

    def get_completions(self, cmd):
        self.get_completions_called += 1
        return self.completions_map.get(cmd)

    def get_commands(self):
        # Return explicit list if provided; otherwise build deterministic union
        if self._commands_list is not None:
            return list(self._commands_list)
        keys = set(self.completions_map.keys()) | set(self.raw_map.keys())
        # include any declared matches
        try:
            matches = self._matching_return[0]
        except Exception:
            matches = []
        if matches:
            for m in matches:
                keys.add(m)
        return sorted(keys)


def _list_texts_and_positions(gen):
    # Consume generator and return list of (text, start_position)
    return [(c.text, c.start_position) for c in list(gen)]


def test_single_word_partial_yields_candidates_round_131():
    # Patch Completion to avoid prompt_toolkit dependency
    io_mod.Completion = SimpleCompletion

    # Create an AutoCompleter with simple command_names
    commands = DummyCommands(([], None, None))
    ac = AutoCompleter(None, [], [], commands, 'utf-8', [])
    ac.command_names = ['foo', 'foobar', 'bar']
    ac.command_completions = {}

    # When user is typing a single token and last char is not whitespace,
    # the function returns command names that start with the partial
    completions = list(ac.get_command_completions(None, None, 'fo', ['fo']))
    # Expect two completions, sorted alphabetically
    assert _list_texts_and_positions(completions) == [('foo', -2), ('foobar', -2)]


def test_return_on_space_or_single_round_131():
    io_mod.Completion = SimpleCompletion

    commands = DummyCommands(([], None, None))
    ac = AutoCompleter(None, [], [], commands, 'utf-8', [])
    ac.command_names = ['any']
    ac.command_completions = {}

    # If the text ends with whitespace, or len(words) <= 1 (and not handled by first branch),
    # the function should return nothing.
    empty = list(ac.get_command_completions(None, None, 'cmd ', ['cmd']))
    assert empty == []


def test_matching_commands_raw_completer_yields_round_131():
    io_mod.Completion = SimpleCompletion

    # matching_commands returns single match so cmd will be replaced
    # Provide a raw completer for that resolved command
    def raw_completer(document, complete_event):
        yield io_mod.Completion('raw_suggestion', start_position=-3)
        yield io_mod.Completion('raw_second', start_position=-3)

    commands = DummyCommands((['alias_cmd'], None, None), raw_map={'alias_cmd': raw_completer})
    ac = AutoCompleter(None, [], [], commands, 'utf-8', [])
    ac.command_completions = {}

    # Provide two words so first single-word branch does not trigger
    results = list(ac.get_command_completions(None, None, 'cmd par', ['cmd', 'par']))
    assert _list_texts_and_positions(results) == [('raw_suggestion', -3), ('raw_second', -3)]


def test_matching_commands_cmd_not_in_matches_returns_round_131():
    io_mod.Completion = SimpleCompletion

    # matching_commands returns a list that does not contain the original cmd
    commands = DummyCommands((['some_other'], None, None))
    ac = AutoCompleter(None, [], [], commands, 'utf-8', [])
    ac.command_completions = {}

    out = list(ac.get_command_completions(None, None, 'cmd arg', ['cmd', 'arg']))
    # Since cmd ('cmd') not in matches and len(matches) != 1, the function returns nothing
    assert out == []


def test_get_completions_none_returns_round_131():
    io_mod.Completion = SimpleCompletion

    # matching_commands resolves to the command (len == 1), but get_completions returns None
    commands = DummyCommands((['cmd'], None, None), raw_map={}, completions_map={'cmd': None})
    ac = AutoCompleter(None, [], [], commands, 'utf-8', [])
    ac.command_completions = {}

    out = list(ac.get_command_completions(None, None, 'cmd arg', ['cmd', 'arg']))
    # Should return nothing and cache the None result
    assert out == []
    assert ac.command_completions.get('cmd') is None


def test_cached_and_filter_candidates_round_131():
    io_mod.Completion = SimpleCompletion

    # matching_commands resolves to the command; completions provided once
    completions_list = ['ParamOne', 'OtherThing', 'another']
    commands = DummyCommands((['cmd'], None, None), completions_map={'cmd': completions_list})
    ac = AutoCompleter(None, [], [], commands, 'utf-8', [])
    ac.command_completions = {}

    # First call should populate the cache and return filtered results (case-insensitive)
    first = list(ac.get_command_completions(None, None, 'cmd one', ['cmd', 'one']))
    assert _list_texts_and_positions(first) == [('ParamOne', -3)]
    # Ensure completions were requested exactly once
    assert commands.get_completions_called == 1
    assert ac.command_completions['cmd'] is completions_list

    # Second call should use cached value (get_completions should not be called again)
    second = list(ac.get_command_completions(None, None, 'cmd one', ['cmd', 'one']))
    assert _list_texts_and_positions(second) == [('ParamOne', -3)]
    assert commands.get_completions_called == 1
