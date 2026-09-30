import pytest

from sweagent.run.common import AutoCorrectSuggestion


def test_init_raises_on_both_help_and_alternative_round_014():
    # If both help and alternative are provided, __init__ should raise a ValueError
    with pytest.raises(ValueError) as exc:
        AutoCorrectSuggestion('orig', 'alt', help='conflict')
    assert str(exc.value) == "Cannot set both help and alternative"


def test_show_splits_and_detects_original_round_014():
    # When an arg contains '=', it is split; otherwise appended as-is.
    s = AutoCorrectSuggestion('foo', 'bar')
    # '=' case: should split into ['--foo', '123'] and detect '--foo'
    assert s.show(['--foo=123']) is True
    # '=' case where original is not present
    assert s.show(['--other=1']) is False
    # no '=' case: appended element should be matched directly
    assert s.show(['--foo']) is True


def test_show_with_condition_invoked_round_014():
    # If a condition is provided, show() must call it with the normalized args
    captured = {}

    def cond(no_equal):
        # capture the incoming list and return whether the original flag exists
        captured['seen'] = list(no_equal)
        return '--foo' in no_equal

    s = AutoCorrectSuggestion('foo', '', condition=cond)
    res = s.show(['--foo=1'])
    assert res is True
    # ensure the condition was called with the split pieces
    assert captured['seen'] == ['--foo', '1']

    # also ensure a condition that returns False is respected
    def cond_false(no_equal):
        return False

    s2 = AutoCorrectSuggestion('foo', '', condition=cond_false)
    assert s2.show(['--foo=1']) is False


def test_format_prefers_help_over_alternative_round_014():
    # If help is provided, format() should return help verbatim
    # Smallest repair: do not pass a non-empty alternative together with help
    s = AutoCorrectSuggestion('foo', help='explicit help')
    assert s.format() == 'explicit help'

    # Otherwise format() should return the suggestion message including both original and alternative
    s2 = AutoCorrectSuggestion('foo', 'bar')
    assert s2.format() == 'You wrote [red]--foo[/red]. Did you mean [green]--bar[/green]?'
