# file: browser_use/actor/utils.py:7-160
# asked: {"lines": [22, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 96, 97, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 151, 152, 154, 155, 157, 160], "branches": [[147, 148], [147, 151], [151, 152], [151, 160], [152, 154], [152, 155], [155, 157], [155, 160]]}
# gained: {"lines": [22, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 96, 97, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 151, 152, 154, 155, 157, 160], "branches": [[147, 148], [147, 151], [151, 152], [151, 160], [152, 154], [152, 155], [155, 157], [155, 160]]}

import pytest

from browser_use.actor.utils import Utils


def test_known_key_map_entries():
    # Test several keys that should be present in the internal key_map
    assert Utils.get_key_info('Enter') == ('Enter', 13)
    assert Utils.get_key_info(' ') == ('Space', 32)
    assert Utils.get_key_info('Space') == ('Space', 32)
    assert Utils.get_key_info(';') == ('Semicolon', 186)
    assert Utils.get_key_info('Semicolon') == ('Semicolon', 186)
    assert Utils.get_key_info('F12') == ('F12', 123)
    assert Utils.get_key_info('Numpad3') == ('Numpad3', 99)
    assert Utils.get_key_info('AudioVolumeUp') == ('AudioVolumeUp', 175)
    assert Utils.get_key_info('PrintScreen') == ('PrintScreen', 44)
    # Modifier / meta keys
    assert Utils.get_key_info('Meta') == ('MetaLeft', 91)
    assert Utils.get_key_info('ShiftRight') == ('ShiftRight', 16)
    # Punctuation and special characters
    assert Utils.get_key_info('\\') == ('Backslash', 220)
    assert Utils.get_key_info("'") == ('Quote', 222)


def test_alphanumeric_dynamic_handling():
    # Lowercase alphabetic -> KeyX with uppercase ord
    code, vk = Utils.get_key_info('a')
    assert code == 'KeyA'
    assert vk == ord('A') == 65

    # Uppercase alphabetic -> KeyX with uppercase ord (same behavior)
    code, vk = Utils.get_key_info('Z')
    assert code == 'KeyZ'
    assert vk == ord('Z') == 90

    # Digit handling -> DigitN with ASCII code
    code, vk = Utils.get_key_info('5')
    assert code == 'Digit5'
    assert vk == ord('5') == 53

    # Single non-alphanumeric character that is not in map should fall back
    # Use a single character that is not in the key_map and not alnum, e.g., '~'
    code, vk = Utils.get_key_info('~')
    assert code == '~'
    assert vk is None


def test_fallback_for_unknown_multi_char_keys():
    # Unknown multi-character key should return (key, None)
    unknown = 'SomeUnknownKey'
    assert Utils.get_key_info(unknown) == (unknown, None)

    # Two-character alpha string should NOT be treated as single-character alpha
    assert Utils.get_key_info('ab') == ('ab', None)
