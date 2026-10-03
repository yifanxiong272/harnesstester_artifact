def test_probe_001():
    # Import only the public entrypoint under test
    from pr_agent.algo.utils import load_yaml

    # Activation condition: response_text begins exactly with uppercase fence '```YAML'
    fenced = "```YAML\nname: Alice\nage: 30\n```"

    # Independent expected outcome (equivalent to yaml.safe_load of the inner content)
    expected = {'name': 'Alice', 'age': 30}

    # Exercise the focused unit and assert the externally observable consequence
    result = load_yaml(fenced)

    # Primary behavioral oracle: load_yaml must parse the inner YAML regardless of fence case
    assert result == expected, f"load_yaml failed to parse uppercase-fenced YAML correctly; got: {result!r}"
