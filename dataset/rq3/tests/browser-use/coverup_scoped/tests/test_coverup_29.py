# file: browser_use/cli.py:354-397
# asked: {"lines": [354, 356, 357, 358, 361, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 381, 382, 384, 387, 388, 389, 390, 391, 392, 394, 395, 397], "branches": [[363, 364], [363, 387], [364, 365], [364, 369], [365, 366], [365, 368], [369, 370], [369, 374], [370, 371], [370, 373], [374, 375], [374, 379], [375, 376], [375, 378], [379, 381], [379, 387], [387, 388], [387, 389], [389, 390], [389, 391], [391, 392], [391, 394]]}
# gained: {"lines": [354, 356, 357, 358, 361, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372, 374, 375, 376, 377, 379, 381, 382, 384, 387, 388, 389, 390, 391, 392, 394, 395, 397], "branches": [[363, 364], [363, 387], [364, 365], [364, 369], [365, 366], [365, 368], [369, 370], [369, 374], [370, 371], [374, 375], [374, 379], [375, 376], [379, 381], [387, 388], [387, 389], [389, 390], [389, 391], [391, 392], [391, 394]]}

import pytest
from types import SimpleNamespace

import browser_use.cli as cli


class DummyOpenAI:
    def __init__(self, model, temperature, api_key):
        self.model = model
        self.temperature = temperature
        self.api_key = api_key


class DummyAnthropic:
    def __init__(self, model, temperature):
        self.model = model
        self.temperature = temperature


class DummyGoogle:
    def __init__(self, model, temperature):
        self.model = model
        self.temperature = temperature


def _set_dummy_classes(monkeypatch):
    monkeypatch.setattr(cli, "ChatOpenAI", DummyOpenAI)
    monkeypatch.setattr(cli, "ChatAnthropic", DummyAnthropic)
    monkeypatch.setattr(cli, "ChatGoogle", DummyGoogle)


def _set_config(monkeypatch, openai=None, anthropic=None, google=None):
    # CONFIG is an object imported in cli module; patch its attributes
    # Use raising=False in case attributes don't exist (they should)
    monkeypatch.setattr(cli.CONFIG, "OPENAI_API_KEY", openai, raising=False)
    monkeypatch.setattr(cli.CONFIG, "ANTHROPIC_API_KEY", anthropic, raising=False)
    monkeypatch.setattr(cli.CONFIG, "GOOGLE_API_KEY", google, raising=False)


def test_get_llm_gpt_with_model_api_key(monkeypatch):
    _set_dummy_classes(monkeypatch)
    # No global OPENAI key, but model-provided key present
    _set_config(monkeypatch, openai=None, anthropic=None, google=None)

    config = {"model": {"name": "gpt-test", "temperature": 0.42, "api_keys": {"OPENAI_API_KEY": "model-key"}}}

    llm = cli.get_llm(config)
    assert isinstance(llm, DummyOpenAI)
    assert llm.model == "gpt-test"
    assert llm.temperature == 0.42
    assert llm.api_key == "model-key"


def test_get_llm_gpt_with_global_openai(monkeypatch):
    _set_dummy_classes(monkeypatch)
    # No model api key, but global CONFIG.OPENAI_API_KEY present
    _set_config(monkeypatch, openai="global-openai", anthropic=None, google=None)

    config = {"model": {"name": "gpt-test2", "temperature": 0.1, "api_keys": {}}}

    llm = cli.get_llm(config)
    assert isinstance(llm, DummyOpenAI)
    assert llm.model == "gpt-test2"
    assert llm.temperature == 0.1
    assert llm.api_key == "global-openai"


def test_get_llm_gpt_missing_keys_exits(monkeypatch, capsys):
    _set_dummy_classes(monkeypatch)
    # No model api key and no global openai key -> should exit with warning
    _set_config(monkeypatch, openai=None, anthropic=None, google=None)

    config = {"model": {"name": "gpt-no-key", "temperature": 0.0, "api_keys": {}}}

    with pytest.raises(SystemExit) as exc:
        cli.get_llm(config)
    captured = capsys.readouterr()
    assert "OpenAI API key not found" in captured.out
    assert exc.value.code == 1


def test_get_llm_claude_requires_anthropic_key(monkeypatch, capsys):
    _set_dummy_classes(monkeypatch)
    # Ensure ANTHROPIC_API_KEY is missing -> exit
    _set_config(monkeypatch, openai=None, anthropic=None, google=None)

    config = {"model": {"name": "claude-2", "temperature": 0.2}}

    with pytest.raises(SystemExit) as exc:
        cli.get_llm(config)
    captured = capsys.readouterr()
    assert "Anthropic API key not found" in captured.out
    assert exc.value.code == 1


def test_get_llm_gemini_requires_google_key(monkeypatch, capsys):
    _set_dummy_classes(monkeypatch)
    # Ensure GOOGLE_API_KEY is missing -> exit
    _set_config(monkeypatch, openai=None, anthropic=None, google=None)

    config = {"model": {"name": "gemini-pro", "temperature": 0.3}}

    with pytest.raises(SystemExit) as exc:
        cli.get_llm(config)
    captured = capsys.readouterr()
    assert "Google API key not found" in captured.out
    assert exc.value.code == 1


def test_get_llm_oci_models_exit(monkeypatch, capsys):
    _set_dummy_classes(monkeypatch)
    # Any config for OCI model should print message and exit
    _set_config(monkeypatch, openai="x", anthropic="y", google="z")

    config = {"model": {"name": "oci-custom", "temperature": 0.8}}

    with pytest.raises(SystemExit) as exc:
        cli.get_llm(config)
    captured = capsys.readouterr()
    assert "OCI models require manual configuration" in captured.out
    assert exc.value.code == 1


def test_auto_detect_prefers_openai(monkeypatch):
    _set_dummy_classes(monkeypatch)
    # No model name; global OPENAI set -> should return OpenAI default
    _set_config(monkeypatch, openai="env-openai", anthropic=None, google=None)

    config = {}
    llm = cli.get_llm(config)
    assert isinstance(llm, DummyOpenAI)
    assert llm.model == "gpt-5-mini"
    assert llm.api_key == "env-openai"


def test_auto_detect_anthropic_when_no_openai(monkeypatch):
    _set_dummy_classes(monkeypatch)
    # No OPENAI, but ANTHROPIC set
    _set_config(monkeypatch, openai=None, anthropic="env-anthropic", google=None)

    config = {}
    llm = cli.get_llm(config)
    assert isinstance(llm, DummyAnthropic)
    assert llm.model == "claude-4-sonnet"
    assert llm.temperature == 0.0  # default temperature when not provided


def test_auto_detect_google_when_only_google(monkeypatch):
    _set_dummy_classes(monkeypatch)
    # Only GOOGLE set
    _set_config(monkeypatch, openai=None, anthropic=None, google="env-google")

    config = {}
    llm = cli.get_llm(config)
    assert isinstance(llm, DummyGoogle)
    assert llm.model == "gemini-2.5-pro"
    assert llm.temperature == 0.0


def test_auto_detect_no_keys_exits(monkeypatch, capsys):
    _set_dummy_classes(monkeypatch)
    # No keys anywhere -> should exit with message
    _set_config(monkeypatch, openai=None, anthropic=None, google=None)

    config = {}
    with pytest.raises(SystemExit) as exc:
        cli.get_llm(config)
    captured = capsys.readouterr()
    assert "No API keys found" in captured.out
    assert exc.value.code == 1
