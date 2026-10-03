def test_probe_001_decode_unicode_escapes_with_non_latin1():
    # Import only the declared public entrypoint for this target unit
    from browser_use.agent.gif import decode_unicode_escapes_to_utf8

    # Construct input deterministically: a literal backslash-u escape plus an emoji
    text = "\\u4e2d" + "😊"

    # Execute the target function
    result = decode_unicode_escapes_to_utf8(text)

    # Primary behavioral oracle: the \u4e2d escape should become the character '中' and the emoji must be preserved
    assert result == "中" + "😊"
