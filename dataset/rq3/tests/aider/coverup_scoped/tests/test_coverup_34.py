# file: aider/models.py:1302-1319
# asked: {"lines": [1303, 1304, 1305, 1307, 1308, 1309, 1311, 1312, 1314, 1315, 1316, 1317, 1319], "branches": [[1303, 1304], [1303, 1307], [1307, 1308], [1307, 1311], [1314, 1315], [1314, 1319], [1316, 0], [1316, 1317]]}
# gained: {"lines": [1303, 1304, 1305, 1307, 1308, 1309, 1311, 1312, 1314, 1315, 1316, 1317, 1319], "branches": [[1303, 1304], [1303, 1307], [1307, 1308], [1307, 1311], [1314, 1315], [1314, 1319], [1316, 0], [1316, 1317]]}

import sys
import pytest

import aider.models as models


def test_main_no_args_raises_and_prints_usage(capsys):
    # Simulate running with no arguments (len(sys.argv) < 2)
    orig_argv = sys.argv
    try:
        sys.argv = ["models.py"]
        with pytest.raises(SystemExit) as excinfo:
            models.main()
        # sys.exit(1) should raise SystemExit with code 1
        assert excinfo.value.code == 1

        captured = capsys.readouterr()
        assert "Usage: python models.py <model_name> or python models.py --yaml" in captured.out
    finally:
        sys.argv = orig_argv


def test_main_yaml_prints_yaml_string(monkeypatch, capsys):
    # Simulate argv requesting YAML output
    monkeypatch.setattr(sys, "argv", ["models.py", "--yaml"])

    # Patch get_model_settings_as_yaml to return a known string
    monkeypatch.setattr(models, "get_model_settings_as_yaml", lambda: "model: test_yaml\n")

    # Call main and capture output
    models.main()
    captured = capsys.readouterr()
    assert "model: test_yaml" in captured.out


def test_main_with_matching_models_prints_list(monkeypatch, capsys):
    # Simulate argv requesting fuzzy match for a model name
    monkeypatch.setattr(sys, "argv", ["models.py", "gpt-test"])

    # Patch fuzzy_match_models to return a non-empty list
    monkeypatch.setattr(models, "fuzzy_match_models", lambda name: ["gpt-test-1", "gpt-test-2"])

    models.main()
    captured = capsys.readouterr()
    assert "Matching models for 'gpt-test':" in captured.out
    assert "gpt-test-1" in captured.out
    assert "gpt-test-2" in captured.out


def test_main_with_no_matching_models_prints_no_match(monkeypatch, capsys):
    # Simulate argv requesting fuzzy match for a model name with no matches
    monkeypatch.setattr(sys, "argv", ["models.py", "nonexistent-model"])

    # Patch fuzzy_match_models to return an empty list
    monkeypatch.setattr(models, "fuzzy_match_models", lambda name: [])

    models.main()
    captured = capsys.readouterr()
    assert "No matching models found for 'nonexistent-model'." in captured.out
