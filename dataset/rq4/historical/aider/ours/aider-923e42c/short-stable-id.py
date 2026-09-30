from aider.utils import replace_most_similar_chunk


def test_probe_001():
    part_lines = [f"PART_LINE_{i}:" + ("x" * 200) for i in range(5)]
    part = "\n".join(part_lines)
    noise_prefix = ["NOISE_BEFORE_1", "NOISE_BEFORE_2"]
    chunk_start = len(noise_prefix)
    whole_lines = noise_prefix + part_lines[:4] + ["NOISE_AFTER_1", "NOISE_AFTER_2"]
    whole = "\n".join(whole_lines)
    replace_text = "REPLACED_LINE"

    result = replace_most_similar_chunk(whole, part, replace_text)

    expected_lines = whole_lines[:chunk_start] + [replace_text] + whole_lines[chunk_start + 4 :]
    expected = "\n".join(expected_lines) + "\n"

    assert result == expected, (
        "Expected the 4-line best-match (the inclusive lower-bound candidate) to be replaced, "
        "but the function returned: {}".format(repr(result))
    )
