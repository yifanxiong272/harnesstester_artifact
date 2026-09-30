def test_probe_001():
    """Probe that try_dotdotdots rejects ambiguous edits where a non-empty chunk appears multiple times in 'whole'.

    The 'part' and 'replace' use explicit '...\n' elision lines so the implementation will parse them into pieces.
    One of the non-empty parsed pieces is the string 'X\n' which appears twice in 'whole'. The correct behavior (oracle)
    is to raise ValueError rather than silently replacing both occurrences.
    """
    from aider.utils import try_dotdotdots
    import pytest

    # 'X\n' appears twice in whole -> ambiguous target
    whole = "pre\nX\nmid\nX\npost\n"

    # Use leading/trailing ... lines so parsed even pieces include an exact 'X\n' piece
    part = "...\nX\n...\n"
    replace = "...\nX_REPLACED\n...\n"

    # Oracle: ambiguous non-empty piece should cause a ValueError
    with pytest.raises(ValueError):
        try_dotdotdots(whole, part, replace)
