def test_probe_001_case_insensitive_fence_parsing_equivalence():
    import yaml
    from pr_agent.algo.utils import load_yaml

    def make_fenced_response(inner_yaml: str) -> str:
        # Activation condition: leading newline then an opening fenced code block with an uppercase language tag
        return "\n```YAML\n" + inner_yaml + "\n```"

    inner = (
        "name: Alice\n"
        "age: 28\n"
        "active: true\n"
        "roles:\n"
        "  - dev\n"
        "  - ops\n"
    )

    response = make_fenced_response(inner)

    # Independent oracle: load_yaml on the fenced input must equal yaml.safe_load of the inner YAML
    expected = yaml.safe_load(inner)
    result = load_yaml(response)

    assert result == expected, f"load_yaml returned {result!r}, expected {expected!r}"
