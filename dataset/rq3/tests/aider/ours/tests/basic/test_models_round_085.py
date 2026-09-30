import sys
import pytest
import aider.models as models


def test_main_no_args_round_085(monkeypatch, capsys):
    # Simulate calling the script with no additional args -> should print usage and exit(1)
    monkeypatch.setattr(sys, "argv", ["models.py"])

    with pytest.raises(SystemExit) as excinfo:
        models.main()

    # Confirm exit code and printed usage message
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == "Usage: python models.py <model_name> or python models.py --yaml\n"


def test_main_yaml_round_085(monkeypatch, capsys):
    # Patch sys.argv to request YAML and patch the provider function to return a deterministic YAML string
    monkeypatch.setattr(sys, "argv", ["models.py", "--yaml"]) 
    monkeypatch.setattr(models, "get_model_settings_as_yaml", lambda: "model: test\nversion: 1")

    # Should print the YAML string and not exit
    models.main()
    captured = capsys.readouterr()
    assert captured.out == "model: test\nversion: 1\n"


def test_main_matching_models_round_085(monkeypatch, capsys):
    # When a model name is provided and fuzzy_match_models returns matches, the header and each model should print
    monkeypatch.setattr(sys, "argv", ["models.py", "gpt"])

    def fake_fuzzy(name):
        # Ensure deterministic ordering and content
        return ["gpt-1", "gpt-2"]

    monkeypatch.setattr(models, "fuzzy_match_models", fake_fuzzy)

    models.main()
    captured = capsys.readouterr()
    expected_header = "Matching models for 'gpt':\n"
    # Printed models appear each on their own line after the header
    expected_models = "gpt-1\ngpt-2\n"
    assert captured.out == expected_header + expected_models


def test_main_no_matching_models_round_085(monkeypatch, capsys):
    # When fuzzy_match_models returns empty, the 'No matching models' message should print
    monkeypatch.setattr(sys, "argv", ["models.py", "unknown-model"])
    monkeypatch.setattr(models, "fuzzy_match_models", lambda name: [])

    models.main()
    captured = capsys.readouterr()
    assert captured.out == "No matching models found for 'unknown-model'.\n"
