def test_probe_001():
    import yaml
    from pr_agent.algo.utils import load_yaml

    # Input uses an opening fence with a single space before the language tag: '``` yaml'
    response_text = "``` yaml\nname: A\nage: 1\n```"

    # Inner YAML that a tolerant parser should extract and parse
    inner_yaml = "name: A\nage: 1\n"

    expected = yaml.safe_load(inner_yaml)

    result = load_yaml(response_text)

    # Primary behavioral oracle: load_yaml must return the same structure as yaml.safe_load on the inner YAML
    assert result == expected, (
        f"load_yaml did not return the expected mapping for opener '``` yaml'.\n"
        f"response_text: {response_text!r}\nexpected: {expected!r}\nactual: {result!r}"
    )
