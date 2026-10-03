import yaml
from pr_agent.algo.utils import load_yaml


def test_probe_001():
    """Probe: ensure load_yaml strips a fenced YAML block even when the fence language tag is uppercased.

    Invariant: for a fenced block, load_yaml(response_text) should equal yaml.safe_load(inner_text)
    where inner_text is the substring between the opening and closing fences. This test uses an
    uppercase language tag ('```YAML') to detect case-sensitive removeprefix behavior.
    """

    # Deterministic inner YAML content that yaml.safe_load parses to a mapping
    inner_yaml = "name: John Smith\nage: 35"

    # Uppercase language tag on opening fence to exercise case sensitivity
    fenced_yaml = "```YAML\n" + inner_yaml + "\n```"

    # Expected result computed independently using yaml.safe_load on the inner content
    expected = yaml.safe_load(inner_yaml)

    # Call the public entrypoint under test
    result = load_yaml(fenced_yaml)

    # Primary oracle: result must exactly match yaml.safe_load(inner_yaml)
    assert result == expected, (
        "load_yaml did not return the same parsed object as yaml.safe_load on the inner content. "
        f"fenced input: {fenced_yaml!r}, expected: {expected!r}, got: {result!r}"
    )
