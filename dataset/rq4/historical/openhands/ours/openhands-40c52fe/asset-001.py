from openhands.resolver.patching.patch import parse_unified_diff, Change


def test_probe_001_default_hunk_count_for_omitted_counts():
    # Minimal unified diff: hunk header omits explicit counts (defaults semantically to 1)
    diff = "@@ -1 +1 @@\n line_of_context\n"

    changes = parse_unified_diff(diff)

    # The independent oracle: omitted counts default to 1, so the single context line
    # should map old==1 and new==1 and preserve the line text without the leading marker.
    assert changes is not None, "parse_unified_diff returned None but expected a list of Change objects"

    # Find any Change matching the expected mapping
    matches = [c for c in changes if getattr(c, 'old', None) == 1 and getattr(c, 'new', None) == 1 and getattr(c, 'line', None) == 'line_of_context']

    assert matches, (
        "Expected a Change with old==1, new==1, line=='line_of_context' but did not find one.\n"
        f"Returned changes: {changes}"
    )
