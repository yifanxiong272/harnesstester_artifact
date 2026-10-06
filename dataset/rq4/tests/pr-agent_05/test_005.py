def test_probe_001():
    # Exercise only the public entrypoint declared in the boundary: load_yaml
    from pr_agent.algo.utils import load_yaml
    import yaml

    # Minimal valid YAML inner document (deterministic)
    inner = 'name: Alice\nage: 30\n'

    # Construct the activation-condition input: opening fence uses uppercase 'YAML'
    fenced = '```YAML\n' + inner + '```'

    # Independent oracle: parsing the inner YAML with yaml.safe_load is the expected behavior
    expected = yaml.safe_load(inner)

    result = load_yaml(fenced)

    # Primary behavioral assertion: the function should return the same structure as yaml.safe_load on the inner content
    assert result == expected, (
        f"load_yaml did not parse fenced YAML with uppercase fence as expected.\n"
        f"input: {fenced!r}\nexpected: {expected!r}\nactual: {result!r}"
    )
