def test_probe_001_case_insensitive_fence_equivalence():
    """Verify that an opening fence using uppercase '```YAML' does not change parsed YAML content.

    Invariant: Stripping surrounding fenced-code markers (regardless of case on the language tag)
    should not change the YAML content; therefore load_yaml(response_with_fence) must equal
    yaml.safe_load(inner_yaml) when inner_yaml is valid.
    """

    import yaml
    from pr_agent.algo.utils import load_yaml

    def make_fenced_yaml(inner: str) -> str:
        # Use an uppercase fence tag as the activation condition requires
        return "```YAML\n" + inner + "\n```"

    # Deterministic, valid YAML covering mapping, boolean, integer, and sequence
    inner_yaml = (
        "name: Alice\n"
        "age: 30\n"
        "active: true\n"
        "scores:\n"
        "  - 10\n"
        "  - 20\n"
    )

    fenced = make_fenced_yaml(inner_yaml)

    # Expected object using the canonical parser
    expected = yaml.safe_load(inner_yaml)

    # Exercise the public entrypoint
    result = load_yaml(fenced)

    # Primary deterministic assertion: external observable equality with yaml.safe_load
    assert result == expected, (
        "load_yaml did not return the same object as yaml.safe_load for an uppercase fence."
    )
