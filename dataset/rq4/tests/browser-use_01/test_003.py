def test_probe_001_decode_with_non_latin1_and_literal_escape():
    """Probe: when input contains a real non-Latin-1 character and a literal backslash-u escape for the same codepoint,
    the function should decode the escape so both positions contain the Unicode character.

    This construction is deterministic: actual_char is the CJK character U+4E2D ("中");
    literal_escape is the raw string r"\\u4e2d" so the runtime input contains two backslashes then 'u'.
    """
    from browser_use.agent.gif import decode_unicode_escapes_to_utf8

    # The actual Unicode character (non-Latin-1)
    actual_char = "中"
    # A literal backslash-u escape for the same codepoint; raw string preserves the backslashes
    literal_escape = r"\\u4e2d"

    inp = actual_char + " " + literal_escape
    expected = actual_char + " " + actual_char

    result = decode_unicode_escapes_to_utf8(inp)

    # Primary oracle: the literal escape should be decoded into the same Unicode character
    assert result == expected, (
        f"Expected decoded output {expected!r} but got {result!r} for input {inp!r}.\n"
        "If this fails, the function may be returning the original text (e.g. due to a latin1 encode error)"
    )
