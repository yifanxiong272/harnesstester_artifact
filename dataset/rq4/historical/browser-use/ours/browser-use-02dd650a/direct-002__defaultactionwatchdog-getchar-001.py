from browser_use.browser.watchdogs.default_action_watchdog import DefaultActionWatchdog


def test_probe_001():
    """Probe _get_char_modifiers_and_vk with U+0130 and assert base_key is a single codepoint.

    This exercises the uppercase branch which returns char.lower(). For U+0130, lowercasing produces
    multiple codepoints ('i' + COMBINING DOT ABOVE). The independent oracle requires base_key length == 1.
    """
    inst = object.__new__(DefaultActionWatchdog)
    modifiers, vk_code, base_key = inst._get_char_modifiers_and_vk('\u0130')
    # Primary behavioral oracle: base_key must be a single character (one Unicode codepoint)
    assert isinstance(base_key, str)
    assert len(base_key) == 1, (
        "base_key must be a single codepoint for input U+0130, "
        f"got length={len(base_key)} value={base_key!r}")
