def test_probe_001_decodes_unicode_escapes_with_non_latin1_chars():
    # Import only the declared public entrypoint
    from browser_use.agent.gif import decode_unicode_escapes_to_utf8

    # Input contains literal backslash-u escapes and a non-Latin-1 emoji character.
    # Use double backslashes in the source so the runtime string contains the literal "\\u" sequences.
    inp = "Hello \\u4f60\\u597d and emoji 💡"

    # Call the target function
    out = decode_unicode_escapes_to_utf8(inp)

    # Expect the \u escapes decoded to Chinese characters and the emoji preserved.
    expected = "Hello 你好 and emoji 💡"

    # Primary behavioral oracle: exact equality
    assert out == expected, f"decode_unicode_escapes_to_utf8 failed: {out!r} != {expected!r}"
