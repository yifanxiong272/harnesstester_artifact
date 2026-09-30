from aider.utils import replace_most_similar_chunk


def test_probe_001():
    whole = (
        "Header line\n"
        "middle one\n"
        "middle two\n"
        "Footer line\n"
    )
    part = "middle one\nmidle two"
    replace = ""
    result = replace_most_similar_chunk(whole, part, replace)
    expected_lines = ["Header line", "Footer line"]
    expected_output = "\n".join(expected_lines)
    if whole.endswith("\n"):
        expected_output += "\n"
    assert result == expected_output, (
        "replace_most_similar_chunk inserted an unexpected blank line or altered trailing newline.\n"
        f"got:    {result!r}\nexpected:{expected_output!r}"
    )
