import pytest
from gpt_researcher.config.config import Config


def test_list_available_with_json_and_non_json_round_152(monkeypatch):
    """When os.listdir returns a mix of .json and non-.json files, only .json names are appended (without suffix)."""
    # Patch os.listdir to deterministically return a mixture
    monkeypatch.setattr(
        'gpt_researcher.config.config.os.listdir',
        lambda path: ['first.json', 'ignore.txt', 'second.json']
    )
    # Ensure CONFIG_DIR exists as an attribute (value irrelevant because listdir is patched)
    monkeypatch.setattr('gpt_researcher.config.config.Config.CONFIG_DIR', '/nonexistent/dir', raising=False)

    result = Config.list_available_configs()

    assert result == ['default', 'first', 'second']


def test_list_available_with_dotjson_edge_case_round_152(monkeypatch):
    """A file named exactly '.json' should produce an empty-string entry after slicing; non-matching case-sensitive names are ignored."""
    monkeypatch.setattr(
        'gpt_researcher.config.config.os.listdir',
        lambda path: ['.json', 'config.JSON', 'README']
    )
    monkeypatch.setattr('gpt_researcher.config.config.Config.CONFIG_DIR', '/another/dir', raising=False)

    result = Config.list_available_configs()

    # Only '.json' matches .endswith('.json') (case-sensitive), file[:-5] on '.json' yields ''
    assert result == ['default', '']


def test_list_available_with_no_files_round_152(monkeypatch):
    """When no files are present, the default config remains the only entry."""
    monkeypatch.setattr('gpt_researcher.config.config.os.listdir', lambda path: [])
    monkeypatch.setattr('gpt_researcher.config.config.Config.CONFIG_DIR', '/empty/dir', raising=False)

    result = Config.list_available_configs()

    assert result == ['default']
