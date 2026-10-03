import yaml
from pr_agent.algo.utils import load_yaml


def test_probe_001_strip_space_after_backticks():
    """Boundary: boundary-001

    Verify that load_yaml strips an opening Markdown YAML fence that contains a space
    between the backticks and the language token ("``` yaml"). The independent
    invariant: the loader should return the same object as yaml.safe_load applied
    to the inner fenced content.
    """
    fenced = "``` yaml\nname: John\n```"
    inner = "name: John"

    expected = yaml.safe_load(inner)
    actual = load_yaml(fenced)

    # Primary behavioral oracle: exact equality with yaml.safe_load(inner)
    assert actual == expected, f"load_yaml returned {actual!r}, expected {expected!r} for input with opening fence '``` yaml'"
