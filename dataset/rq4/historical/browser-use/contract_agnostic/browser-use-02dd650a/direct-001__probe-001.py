import types
from browser_use.actor.element import Element


def test_probe_001():
    """Probe Element._get_char_modifiers_and_vk with '\u00df' (sharp s).

    This verifies the function returns a (int, int, str) 3-tuple and does not
    raise a TypeError when upper()-mapping produces multiple characters.
    """
    self_like = types.SimpleNamespace()
    fn = Element._get_char_modifiers_and_vk
    result = fn(self_like, '\u00df')

    # Primary oracle: shape and types
    assert isinstance(result, tuple), f"expected tuple result, got {type(result)}"
    assert len(result) == 3, f"expected 3-tuple, got length {len(result)}"
    modifiers, vk_code, base_key = result
    assert isinstance(modifiers, int), f"modifiers must be int, got {type(modifiers)}"
    assert isinstance(vk_code, int), f"vk_code must be int, got {type(vk_code)}"
    assert isinstance(base_key, str), f"base_key must be str, got {type(base_key)}"
