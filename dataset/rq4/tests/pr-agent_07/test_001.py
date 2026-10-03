import yaml
from pr_agent.algo.utils import try_fix_yaml


def test_probe_001():
    """Probe try_fix_yaml fourth fallback: ensure exact top-level key names are preserved.

    The function under test slices the original text between occurrences of first_key and last_key
    and then calls .strip().strip('```yaml').strip('`').strip() on that slice. Because str.strip(chars)
    treats the argument as a character set, leading characters that appear in that set (for example 'a'
    from 'yaml') can be removed from the start of a key. This test constructs a deterministic input
    where the slice starts with the first_key exactly and asserts the returned mapping contains the
    original first_key string unchanged.
    """

    # Local helper to build a response_text that causes the function to reach the fourth fallback.
    def build_response_text():
        # Start with an element that makes full-document parsing fail (unbalanced bracket)
        preamble = "{\nSome garbage: [unclosed\n"
        # Valid YAML snippet between first_key and last_key
        yaml_snippet = (
            "\nanalysis:\n"
            "  details:\n"
            "    summary: example\n"
            "issue:\n"
            "  id: 1\n"
            "\n"
        )
        # Trailing garbage to prevent accidental successful full-document parse
        trailer = "Trailing: ???\n"
        return preamble + yaml_snippet + trailer

    response_text = build_response_text()

    # Sanity check: ensure the slice points will be found as the boundary code expects
    assert "\nanalysis:" in response_text or "analysis:" in response_text
    assert "issue:" in response_text

    # Call the public entrypoint only (per boundary plan)
    result = try_fix_yaml(response_text, first_key="analysis", last_key="issue")

    # Primary behavioral oracle (single decisive assertion): the exact top-level key must be present
    assert isinstance(result, dict), "try_fix_yaml should return a mapping when the fallback succeeds"
    # The invariant: the mapping must contain the original first_key string exactly
    assert "analysis" in result, (
        "Expected top-level key 'analysis' to be preserved in the parsed mapping. "
        "If this fails, the function likely stripped leading characters while trimming wrapper text."
    )
    # Also assert the nested structure parsed as expected
    assert result["analysis"] == {"details": {"summary": "example"}}
