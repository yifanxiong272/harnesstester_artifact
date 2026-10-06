from pr_agent.algo.utils import load_yaml
import yaml

def test_probe_001_strip_space_after_backticks_equivalence():
    # Input: a Markdown fenced YAML block with a single space after the backticks
    md = "``` yaml\nname: John Smith\n```"

    # Expected: the same object as parsing the inner YAML with yaml.safe_load
    inner = "name: John Smith"
    expected = yaml.safe_load(inner)

    result = load_yaml(md)

    # Primary oracle: load_yaml should return the same Python object as yaml.safe_load on the inner content
    assert result == expected
