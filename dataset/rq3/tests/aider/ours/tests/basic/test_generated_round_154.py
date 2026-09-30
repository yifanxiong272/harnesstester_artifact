import pytest

from aider.coders import editblock_coder as ebc

# Tests for replace_most_similar_chunk focused on branches around
# handling leading blank lines and try/except around try_dotdotdots.

def test_replace_returns_from_perfect_or_whitespace_with_leading_blank_round_154(monkeypatch):
    # Prepare deterministic prep behavior: mapping of input -> lines
    mapping = {
        "WHOLE1": ["w1", "w2"],
        # part_lines starts with an empty string and length > 2 to trigger the
        # leading-blank-line branch in replace_most_similar_chunk
        "PART1": ["", "x", "y"],
        "REPL1": ["r1"]
    }

    def fake_prep(val):
        # mimic original prep returning (content, lines)
        return val, mapping[val]

    # perfect_or_whitespace should return None on the initial call (with the
    # original part_lines that starts with '') and should return a result when
    # called with the skip_blank_line_part_lines (i.e. ['x', 'y']).
    def fake_perfect_or_whitespace(whole_lines, part_lines, replace_lines):
        if part_lines and part_lines[0] == "x":
            return "REPLACED"
        return None

    monkeypatch.setattr(ebc, "prep", fake_prep)
    monkeypatch.setattr(ebc, "perfect_or_whitespace", fake_perfect_or_whitespace)

    res = ebc.replace_most_similar_chunk("WHOLE1", "PART1", "REPL1")

    assert res == "REPLACED", "Expected early return from perfect_or_whitespace with skipped blank line"


def test_try_dotdotdots_returns_and_exits_round_154(monkeypatch):
    # When perfect_or_whitespace returns None and try_dotdotdots returns a
    # truthy value, replace_most_similar_chunk should return that value.
    mapping = {
        "WHOLE2": ["wa"],
        "PART2": ["a", "b"],  # no leading blank => skip-blank branch not taken
        "REPL2": ["r"]
    }

    def fake_prep(val):
        return val, mapping[val]

    def fake_perfect_or_whitespace(whole_lines, part_lines, replace_lines):
        return None

    def fake_try_dotdotdots(whole, part, replace):
        return "DOTDOT_RESULT"

    monkeypatch.setattr(ebc, "prep", fake_prep)
    monkeypatch.setattr(ebc, "perfect_or_whitespace", fake_perfect_or_whitespace)
    monkeypatch.setattr(ebc, "try_dotdotdots", fake_try_dotdotdots)

    res = ebc.replace_most_similar_chunk("WHOLE2", "PART2", "REPL2")

    assert res == "DOTDOT_RESULT"


def test_try_dotdotdots_raises_valueerror_swallowed_round_154(monkeypatch):
    # When try_dotdotdots raises ValueError it should be swallowed and the
    # function should return None (the explicit 'return' just after the try/except).
    mapping = {
        "WHOLE3": ["w"],
        "PART3": ["p1", "p2"],
        "REPL3": ["r"]
    }

    def fake_prep(val):
        return val, mapping[val]

    def fake_perfect_or_whitespace(whole_lines, part_lines, replace_lines):
        return None

    def raising_try_dotdotdots(whole, part, replace):
        raise ValueError("simulated parse error from try_dotdotdots")

    monkeypatch.setattr(ebc, "prep", fake_prep)
    monkeypatch.setattr(ebc, "perfect_or_whitespace", fake_perfect_or_whitespace)
    monkeypatch.setattr(ebc, "try_dotdotdots", raising_try_dotdotdots)

    res = ebc.replace_most_similar_chunk("WHOLE3", "PART3", "REPL3")

    assert res is None
