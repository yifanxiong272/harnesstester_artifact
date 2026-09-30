import types
import pytest

import aider.io as aio


def _make_dummy(**kwargs):
    """Create a lightweight dummy instance with attributes used by _get_style."""
    class Dummy:
        pass

    d = Dummy()
    # Set defaults for all attributes the method reads
    attrs = [
        "pretty",
        "user_input_color",
        "completion_menu_bg_color",
        "completion_menu_color",
        "completion_menu_current_bg_color",
        "completion_menu_current_color",
    ]
    for a in attrs:
        setattr(d, a, None)
    # Override with provided values
    for k, v in kwargs.items():
        setattr(d, k, v)
    return d


def test_completion_menu_both_colors_round_134(monkeypatch):
    """When both completion_menu_bg_color and completion_menu_color are set,
    they are combined into the 'completion-menu' entry with 'bg:' prefix for bg color.
    """
    # Patch Style.from_dict to return the dict it receives for easy assertions
    monkeypatch.setattr(aio, "Style", types.SimpleNamespace(from_dict=lambda d: d))

    dummy = _make_dummy(
        pretty=True,
        completion_menu_bg_color="red",
        completion_menu_color="white",
    )

    result = aio.InputOutput._get_style(dummy)

    assert isinstance(result, dict)
    # The bg color should be prefixed with 'bg:' and then the color
    assert result.get("completion-menu") == "bg:red white"
    # No current-completion style should be present
    assert "completion-menu.completion.current" not in result


def test_completion_menu_current_both_round_134(monkeypatch):
    """When both completion_menu_current_bg_color and completion_menu_current_color are set,
    they are combined into the 'completion-menu.completion.current' entry with the
    current color prefixed by 'bg:' (as implemented).
    """
    monkeypatch.setattr(aio, "Style", types.SimpleNamespace(from_dict=lambda d: d))

    dummy = _make_dummy(
        pretty=True,
        completion_menu_current_bg_color="blue",
        completion_menu_current_color="yellow",
    )

    result = aio.InputOutput._get_style(dummy)

    assert isinstance(result, dict)
    # Order: bg_color (as-is), then 'bg:current_color'
    assert result.get("completion-menu.completion.current") == "blue bg:yellow"
    # No top-level completion-menu expected
    assert "completion-menu" not in result


def test_all_options_round_134(monkeypatch):
    """When user_input_color and both completion menus are provided, all relevant
    style entries should be present with the correct formatting.
    """
    monkeypatch.setattr(aio, "Style", types.SimpleNamespace(from_dict=lambda d: d))

    dummy = _make_dummy(
        pretty=True,
        user_input_color="green",
        completion_menu_bg_color="red",
        completion_menu_color="white",
        completion_menu_current_bg_color="blue",
        completion_menu_current_color="yellow",
    )

    result = aio.InputOutput._get_style(dummy)

    assert isinstance(result, dict)
    # user_input_color is set on the empty-string key
    assert result.get("") == "green"
    # and the pygments literal string style is composed accordingly
    assert result.get("pygments.literal.string") == "bold italic green"
    # both completion menu entries should exist and be formatted as above
    assert result.get("completion-menu") == "bg:red white"
    assert result.get("completion-menu.completion.current") == "blue bg:yellow"


def test_pretty_false_early_return_round_134(monkeypatch):
    """If pretty is falsy, the method should return whatever Style.from_dict receives
    for the empty dict (here patched to return the dict itself).
    """
    monkeypatch.setattr(aio, "Style", types.SimpleNamespace(from_dict=lambda d: d))

    dummy = _make_dummy(
        pretty=False,
        user_input_color="should-be-ignored",
        completion_menu_bg_color="ignored",
        completion_menu_color="ignored",
        completion_menu_current_bg_color="ignored",
        completion_menu_current_color="ignored",
    )

    result = aio.InputOutput._get_style(dummy)

    # Expect an empty dict since pretty is False and no styles are added
    assert result == {}
