import pytest

from sweagent.run.common import AutoCorrectSuggestion


def test_init_both_help_and_alternative_raises_round_012():
    # When both help and alternative are provided, constructor must raise ValueError with exact message
    with pytest.raises(ValueError) as exc:
        AutoCorrectSuggestion("opt", alternative="alt", help="some-help")
    assert str(exc.value) == "Cannot set both help and alternative"


def test_show_equal_and_non_equal_variants_round_012():
    # Verify behavior when args contain '=' (split path) and when they don't
    s = AutoCorrectSuggestion("opt")

    # simple flag without '=' should be detected
    assert s.show(["--opt"]) is True

    # flag with '=' should be split and detected
    assert s.show(["--opt=value"]) is True

    # other flags should not accidentally match
    assert s.show(["--other=val"]) is False

    # mixed args: ensure the split extends the list and detection still works
    assert s.show(["--other=val", "--opt=1"]) is True


def test_show_with_condition_true_and_false_round_012():
    # Provide a custom condition callable to drive alternate branch
    def cond_contains_trigger(no_equal_list):
        # condition should receive the same no_equal list built by show()
        return "trigger" in no_equal_list

    s_cond = AutoCorrectSuggestion("ignored", condition=cond_contains_trigger)
    # The arg will be split into ["trigger", "1"], so condition should see "trigger" and return True
    assert s_cond.show(["trigger=1"]) is True

    # When trigger is not present, condition should return False
    assert s_cond.show(["something=else"]) is False


def test_format_help_priority_and_default_round_012():
    # If help text is provided, format() returns it verbatim
    s_help = AutoCorrectSuggestion("opt", alternative="alt", help="explicit help text")
    assert s_help.format() == "explicit help text"

    # Otherwise, format returns the suggestion templated string containing original and alternative
    s_fmt = AutoCorrectSuggestion("orig", "alt")
    expected = "You wrote [red]--orig[/red]. Did you mean [green]--alt[/green]?"
    assert s_fmt.format() == expected
