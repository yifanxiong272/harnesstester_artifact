import sys
import pytest
from types import SimpleNamespace
import browser_use.cli as cli


class DummyOpenAI:
    def __init__(self, model, temperature, api_key=None):
        # capture constructor args for assertions
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


def _set_config_keys(monkeypatch, openai=None, anthropic=None, google=None):
    # Ensure the CONFIG object on the cli module has predictable attributes
    # monkeypatch.setattr with raising=False so tests work even if attributes missing
    monkeypatch.setattr(cli.CONFIG, 'OPENAI_API_KEY', openai, raising=False)
    monkeypatch.setattr(cli.CONFIG, 'ANTHROPIC_API_KEY', anthropic, raising=False)
    monkeypatch.setattr(cli.CONFIG, 'GOOGLE_API_KEY', google, raising=False)


def test_gpt_with_explicit_api_key_round_056(monkeypatch):
    # Provide explicit OPENAI_API_KEY in model config; expect ChatOpenAI returned
    monkeypatch.setattr(cli, 'ChatOpenAI', DummyOpenAI)
    _set_config_keys(monkeypatch, openai=None, anthropic=None, google=None)

    cfg = {'model': {'name': 'gpt-super', 'temperature': 0.42, 'api_keys': {'OPENAI_API_KEY': 'explicit-key'}}}
    llm = cli.get_llm(cfg)

    assert isinstance(llm, DummyOpenAI)
    assert llm.model == 'gpt-super'
    assert llm.temperature == 0.42
    assert llm.api_key == 'explicit-key'


def test_gpt_no_api_key_exit_round_056(monkeypatch, capsys):
    # No API key provided anywhere for a gpt model -> prints warning and exits
    monkeypatch.setattr(cli, 'ChatOpenAI', DummyOpenAI)
    _set_config_keys(monkeypatch, openai=None, anthropic=None, google=None)

    cfg = {'model': {'name': 'gpt-unknown', 'temperature': 0.1, 'api_keys': {}}}
    with pytest.raises(SystemExit) as exc:
        cli.get_llm(cfg)
    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert 'OpenAI API key not found' in captured.out


def test_claude_no_config_key_exit_round_056(monkeypatch, capsys):
    # Claude model configured but ANTHROPIC_API_KEY missing -> exit
    monkeypatch.setattr(cli, 'ChatAnthropic', DummyAnthropic)
    _set_config_keys(monkeypatch, openai=None, anthropic=None, google=None)

    cfg = {'model': {'name': 'claude-2', 'temperature': 0.3}}
    with pytest.raises(SystemExit) as exc:
        cli.get_llm(cfg)
    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert 'Anthropic API key not found' in captured.out


def test_claude_with_key_round_056(monkeypatch):
    # Claude model and config has ANTHROPIC_API_KEY -> ChatAnthropic returned
    monkeypatch.setattr(cli, 'ChatAnthropic', DummyAnthropic)
    _set_config_keys(monkeypatch, openai=None, anthropic='anth-key', google=None)

    cfg = {'model': {'name': 'claude-custom', 'temperature': 0.7}}
    llm = cli.get_llm(cfg)

    assert isinstance(llm, DummyAnthropic)
    assert llm.model == 'claude-custom'
    assert llm.temperature == 0.7


def test_gemini_no_key_exit_round_056(monkeypatch, capsys):
    # Gemini model configured but GOOGLE_API_KEY missing -> exit
    monkeypatch.setattr(cli, 'ChatGoogle', DummyGoogle)
    _set_config_keys(monkeypatch, openai=None, anthropic=None, google=None)

    cfg = {'model': {'name': 'gemini-ultra', 'temperature': 0.0}}
    with pytest.raises(SystemExit) as exc:
        cli.get_llm(cfg)
    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert 'Google API key not found' in captured.out


def test_gemini_with_key_round_056(monkeypatch):
    # Gemini model and GOOGLE_API_KEY present -> ChatGoogle returned
    monkeypatch.setattr(cli, 'ChatGoogle', DummyGoogle)
    _set_config_keys(monkeypatch, openai=None, anthropic=None, google='google-key')

    cfg = {'model': {'name': 'gemini-2.0', 'temperature': 0.12}}
    llm = cli.get_llm(cfg)

    assert isinstance(llm, DummyGoogle)
    assert llm.model == 'gemini-2.0'
    assert llm.temperature == 0.12


def test_oci_model_requires_manual_config_round_056(monkeypatch, capsys):
    # OCI model triggers manual configuration message and exit
    _set_config_keys(monkeypatch, openai=None, anthropic=None, google=None)

    cfg = {'model': {'name': 'oci-special', 'temperature': 0.5}}
    with pytest.raises(SystemExit) as exc:
        cli.get_llm(cfg)
    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert 'OCI models require manual configuration' in captured.out


def test_auto_detect_prefers_openai_api_key_from_model_round_056(monkeypatch):
    # No explicit model name; model_config.api_keys contains OPENAI_API_KEY -> OpenAI returned
    monkeypatch.setattr(cli, 'ChatOpenAI', DummyOpenAI)
    _set_config_keys(monkeypatch, openai=None, anthropic=None, google=None)

    cfg = {'model': {'temperature': 0.9, 'api_keys': {'OPENAI_API_KEY': 'from-model-key'}}}
    llm = cli.get_llm(cfg)

    assert isinstance(llm, DummyOpenAI)
    assert llm.model == 'gpt-5-mini'
    assert llm.temperature == 0.9
    assert llm.api_key == 'from-model-key'


def test_auto_detect_uses_config_anthropic_when_openai_missing_round_056(monkeypatch):
    # No model name, OPENAI missing but ANTHROPIC present -> ChatAnthropic returned
    monkeypatch.setattr(cli, 'ChatAnthropic', DummyAnthropic)
    _set_config_keys(monkeypatch, openai=None, anthropic='anthropic-config-key', google=None)

    cfg = {'model': {'temperature': 0.33}}
    llm = cli.get_llm(cfg)

    assert isinstance(llm, DummyAnthropic)
    assert llm.model == 'claude-4-sonnet'
    assert llm.temperature == 0.33


def test_auto_detect_uses_config_google_when_other_keys_missing_round_056(monkeypatch):
    # No model name, only GOOGLE key present -> ChatGoogle returned
    monkeypatch.setattr(cli, 'ChatGoogle', DummyGoogle)
    _set_config_keys(monkeypatch, openai=None, anthropic=None, google='g-config')

    cfg = {'model': {'temperature': 0.11}}
    llm = cli.get_llm(cfg)

    assert isinstance(llm, DummyGoogle)
    assert llm.model == 'gemini-2.5-pro'
    assert llm.temperature == 0.11


def test_no_api_keys_exit_round_056(monkeypatch, capsys):
    # No model name and no keys anywhere -> exit with message
    _set_config_keys(monkeypatch, openai=None, anthropic=None, google=None)
    cfg = {'model': {'temperature': 0.0}}
    with pytest.raises(SystemExit) as exc:
        cli.get_llm(cfg)
    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert 'No API keys found' in captured.out
