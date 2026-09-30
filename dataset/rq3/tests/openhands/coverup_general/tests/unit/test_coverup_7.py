# file: openhands/resolver/patching/patch.py:898-984
# asked: {"lines": [899, 901, 903, 904, 905, 906, 908, 909, 910, 911, 912, 913, 914, 915, 916, 917, 918, 920, 921, 922, 923, 924, 925, 928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 950, 953, 954, 957, 958, 959, 960, 961, 962, 964, 965, 966, 967, 968, 969, 970, 971, 972, 973, 974, 975, 976, 977, 978, 981, 982, 984], "branches": [[912, 913], [912, 984], [913, 914], [913, 920], [915, 916], [915, 920], [920, 921], [920, 928], [922, 923], [922, 928], [928, 929], [928, 938], [930, 931], [930, 933], [934, 936], [934, 957], [938, 939], [938, 957], [939, 940], [939, 942], [942, 943], [942, 953], [943, 944], [943, 949], [957, 958], [957, 966], [959, 960], [959, 961], [962, 912], [962, 964], [966, 912], [966, 967], [967, 968], [967, 970], [970, 971], [970, 981], [971, 972], [971, 977]]}
# gained: {"lines": [899, 901, 903, 904, 905, 906, 908, 909, 910, 911, 912, 913, 914, 915, 916, 917, 918, 920, 921, 922, 923, 924, 925, 928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 950, 953, 954, 957, 958, 959, 960, 961, 962, 966, 967, 968, 969, 970, 971, 972, 973, 974, 975, 976, 977, 978, 984], "branches": [[912, 913], [912, 984], [913, 914], [913, 920], [915, 916], [920, 921], [920, 928], [922, 923], [928, 929], [928, 938], [930, 931], [930, 933], [934, 936], [934, 957], [938, 939], [939, 940], [939, 942], [942, 943], [942, 953], [943, 944], [957, 958], [957, 966], [959, 960], [959, 961], [962, 912], [966, 967], [967, 968], [967, 970], [970, 971], [971, 972]]}

import zlib

from openhands.resolver.patching.patch import parse_git_binary_diff


def _make_base85_lines_with_padding(data: bytes, prefix: str = "A"):
    """
    Return (padded_data, lines) where padded_data is data possibly extended with
    zero bytes so that base85-encoding of zlib.compress(padded_data) has length
    that is a multiple of 5. The returned lines are prefix + 5-char chunks,
    so each line length >= 6 and (len(line)-1)%5==0.
    """
    for pad in range(0, 50):
        candidate = data + (b"\x00" * pad)
        compressed = zlib.compress(candidate)
        encoded = __import__("base64").b85encode(compressed).decode("ascii")
        if len(encoded) % 5 == 0 and len(encoded) >= 5:
            chunks = [encoded[i:i + 5] for i in range(0, len(encoded), 5)]
            lines = [prefix + chunk for chunk in chunks]
            return candidate, lines
    raise RuntimeError("Could not produce suitable base85 encoding")


def test_parse_git_binary_diff_produces_added_and_removed_changes():
    # Prepare payloads (helpers will pad if necessary)
    added_base = b"added-binary-payload"
    removed_base = b"\x00\x01removed-binary"

    # Create base85 lines suitable for the parser
    added_data_full, added_lines_full = _make_base85_lines_with_padding(added_base, prefix="A")
    removed_data_full, removed_lines_full = _make_base85_lines_with_padding(removed_base, prefix="B")

    # Construct sequence to force both removed and added decodes:
    # 1) literal for added, supply at least one base85 chunk for added
    # 2) then a literal for removed on its own line -> this will clear the in-progress new block
    #    and set old_size (per code logic)
    # 3) provide base85 chunks for removed and a blank line to trigger decode -> produces removed Change
    # 4) finally provide literal for added again with full chunks and blank to trigger decode -> produces added Change
    lines = []
    lines.append("diff --git a/f b/f")
    lines.append("index aaa..bbb")
    # Start an added literal and give one chunk (will be interrupted)
    lines.append(f"literal {len(added_data_full)}")
    # give one chunk (valid base85 chunk)
    lines.append(added_lines_full[0])
    # Now place a literal for removed which will clear the pending new and set old_size
    lines.append(f"literal {len(removed_data_full)}")
    # Provide all removed chunks
    lines.extend(removed_lines_full)
    # blank line triggers decode for removed (old) block
    lines.append("")
    # Now provide the added literal again and all chunks, then blank to decode added
    lines.append(f"literal {len(added_data_full)}")
    lines.extend(added_lines_full)
    lines.append("")

    changes = parse_git_binary_diff(lines)

    # We expect two changes: one removed (old) and one added (new), order depends on how parser handled them.
    assert isinstance(changes, list)
    assert len(changes) == 2

    # Identify which is removed vs added by inspecting fields of the namedtuple:
    # removed change has old == 0 and hunk == removed_data_full
    # added change has old is None and new == 0 and line == added_data_full
    removed = None
    added = None
    for ch in changes:
        if getattr(ch, "old") == 0 and getattr(ch, "hunk") is not None:
            removed = ch
        if getattr(ch, "old") is None and getattr(ch, "new") == 0 and getattr(ch, "line") is not None:
            added = ch

    assert removed is not None, f"Removed change not found in {changes}"
    assert added is not None, f"Added change not found in {changes}"

    assert removed.hunk == removed_data_full
    assert added.line == added_data_full


def test_parse_git_binary_diff_delta_and_invalid_branches():
    # This test exercises delta-handling and the invalid-line clearing path.
    new_base = b"new-data-invalid-branch"
    old_base = b"old-data-invalid-branch"

    # Ensure at least one 5-char chunk is available for initial chunk usage
    new_data, new_lines = _make_base85_lines_with_padding(new_base, prefix="A")
    old_data, old_lines = _make_base85_lines_with_padding(old_base, prefix="B")

    parts = []
    parts.append("diff --git a/f2 b/f2")
    parts.append("index 111..222")
    # Unsupported delta for new
    parts.append("delta 123")
    # literal for new
    parts.append(f"literal {len(new_data)}")
    # one valid base85 chunk
    parts.append(new_lines[0])
    # now an invalid non-base85 non-empty line to trigger clearing branch
    parts.append("THIS IS NOT BASE85")
    # unsupported delta for old
    parts.append("delta 321")
    # literal for old
    parts.append(f"literal {len(old_data)}")
    # one valid chunk
    parts.append(old_lines[0])
    # invalid line containing space so base85 won't match -> triggers clearing branch
    parts.append("! invalid? with spaces!")

    text = "\n".join(parts)
    changes = parse_git_binary_diff(text)

    # Because encoded blocks were intentionally broken, no successful decodes should happen.
    assert isinstance(changes, list)
    assert len(changes) == 0
