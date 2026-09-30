def test_probe_001():
    # Import only the declared public entrypoint
    from openhands.resolver.patching.patch import parse_unified_diff

    # Input: single-hunk unified diff header with omitted lengths and one context line
    diff = "@@ -1 +1 @@\n x\n"

    changes = parse_unified_diff(diff)

    # Basic observable: must return a non-empty list for this single context line hunk
    assert isinstance(changes, list) and len(changes) >= 1, "parse_unified_diff must return a non-empty list for a single-hunk diff"

    first = changes[0]

    # Robust extraction: prefer sequence indexing (namedtuple/tuple), otherwise try common attribute names
    try:
        old_lineno = first[0]
        new_lineno = first[1]
        line_text = first[2]
    except Exception:
        old_lineno = getattr(first, 'old_lineno', getattr(first, 'old', getattr(first, 'a_lineno', None)))
        new_lineno = getattr(first, 'new_lineno', getattr(first, 'new', getattr(first, 'b_lineno', None)))
        line_text = getattr(first, 'line', getattr(first, 'text', getattr(first, 'content', None)))

    # Primary behavioral oracle: both old and new numbers must be 1 and the stored text must match the provided context content 'x'
    assert old_lineno == 1 and new_lineno == 1 and line_text == 'x', (
        f"Expected a single context Change at (1,1,'x'), got ({old_lineno},{new_lineno},{line_text!r})"
    )
