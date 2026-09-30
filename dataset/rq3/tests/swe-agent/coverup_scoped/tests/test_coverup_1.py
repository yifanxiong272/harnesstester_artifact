# file: sweagent/run/common.py:219-359
# asked: {"lines": [265, 266, 268, 269, 271, 272, 273, 274, 275, 276, 287, 288, 301, 302, 306, 316, 317, 318, 319, 321, 324, 325, 326, 328, 331, 332, 333, 335, 338, 339, 340, 343, 344, 345, 346, 347, 348, 349, 350, 353, 354], "branches": [[247, 253], [264, 265], [265, 266], [265, 268], [270, 271], [272, 273], [272, 274], [286, 287], [291, 306], [300, 301], [352, 353]]}
# gained: {"lines": [265, 266, 268, 269, 271, 272, 273, 274, 275, 276, 287, 288, 301, 302, 306, 316, 317, 318, 319, 321, 324, 325, 326, 328, 331, 332, 333, 335, 338, 339, 340, 343, 344, 345, 346, 347, 348, 349, 350, 353, 354], "branches": [[247, 253], [264, 265], [265, 266], [265, 268], [270, 271], [272, 273], [286, 287], [291, 306], [300, 301], [352, 353]]}

import sys
import importlib
from pathlib import Path
import yaml
import pytest

import sweagent.run.common as common
from pydantic import BaseModel, ValidationError
from pydantic_settings import BaseSettings, SettingsError


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []

    def info(self, msg):
        self.infos.append(msg)

    def warning(self, msg):
        self.warnings.append(msg)


class DummyConfig:
    def __init__(self, data=None):
        self._data = data or {}
        self._config_files = []

    def model_dump(self):
        return dict(self._data)


def _make_basiccli():
    # Provide a minimal BaseSettings subclass as config_type
    class DummySettings(BaseSettings):
        pass

    cli = common.BasicCLI(DummySettings)
    # override logger and maybe_show_auto_correct for deterministic behavior
    cli.logger = DummyLogger()
    cli._auto_correct_shown = False

    def maybe_show_auto_correct(args):
        cli._auto_correct_shown = True

    cli.maybe_show_auto_correct = maybe_show_auto_correct
    return cli


def test_help_with_and_without_help_text(monkeypatch, capsys):
    # Case 1: help_text present => rich_print(self.help_text) path
    cli = _make_basiccli()
    cli.default_settings = False
    cli.help_text = "SOME HELP TEXT"
    with pytest.raises(SystemExit) as exc:
        cli.get_config(["--help"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "SOME HELP TEXT" in captured.out

    # Case 2: help_text absent => parser.print_help() path
    cli2 = _make_basiccli()
    cli2.default_settings = False
    cli2.help_text = ""
    with pytest.raises(SystemExit) as exc2:
        cli2.get_config(["--help"])
    assert exc2.value.code == 0
    out = capsys.readouterr().out
    assert "usage" in out.lower()


def test_help_option_uses_confighelper_and_triggers_import(monkeypatch, tmp_path, capsys):
    cli = _make_basiccli()
    cli.default_settings = False

    # Create a temporary module to force the __import__ path to be executed
    mod_name = "tmp_help_mod_for_test"
    mod_file = tmp_path / (mod_name + ".py")
    mod_file.write_text("class TheType:\n    pass\n")
    # Ensure it's importable by inserting tmp_path into sys.path
    monkeypatch.syspath_prepend(str(tmp_path))

    # Ensure module not already imported
    if mod_name in sys.modules:
        monkeypatch.setitem(sys.modules, mod_name, None)

    # Provide a ConfigHelper that returns a predictable string
    class CH:
        def get_help(self, t):
            return f"HELP FOR {t.__name__}"

    monkeypatch.setattr(common, "ConfigHelper", CH)

    # Use the newly created module and type name
    help_option_value = f"{mod_name}.TheType"

    # Call get_config; it should import the module and then exit(0)
    with pytest.raises(SystemExit) as exc:
        cli.get_config(["--help_option", help_option_value])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "HELP FOR TheType" in out


def test_config_file_empty_and_config_files_attached(monkeypatch, tmp_path):
    cli = _make_basiccli()
    cli.default_settings = False

    # Create empty config file
    cfg = tmp_path / "empty.yaml"
    cfg.write_text("   \n")  # whitespace -> treated as empty by .strip()

    # Monkeypatch CliApp.run to return a DummyConfig
    def fake_run(arg_type, remaining_args, **kwargs):
        return DummyConfig({"from_cli": dict(remaining_args)})

    monkeypatch.setattr(common.CliApp, "run", staticmethod(fake_run))

    result = cli.get_config(["--config", str(cfg)])
    # logger should have recorded a warning about empty config file
    assert any(str(cfg) in msg for msg in cli.logger.warnings)
    # returned config should have attached _config_files containing the Path
    assert getattr(result, "_config_files", []) == [cfg]


def test_default_config_empty_triggers_warning(monkeypatch, tmp_path):
    cli = _make_basiccli()
    cli.default_settings = True

    # Create a fake CONFIG_DIR/default.yaml empty
    fake_config_dir = tmp_path / "cfgdir"
    fake_config_dir.mkdir()
    default_file = fake_config_dir / "default.yaml"
    default_file.write_text("   \n")

    monkeypatch.setattr(common, "CONFIG_DIR", fake_config_dir)

    # Monkeypatch CliApp.run to return DummyConfig
    def fake_run(arg_type, remaining_args, **kwargs):
        return DummyConfig({"ok": True})

    monkeypatch.setattr(common.CliApp, "run", staticmethod(fake_run))

    result = cli.get_config([])
    # logger.info should have been called about loading default
    assert any("Loading default config" in msg for msg in cli.logger.infos)
    # logger.warning should have recorded default empty
    assert any(str(default_file) in msg for msg in cli.logger.warnings)
    assert getattr(result, "_config_files", [])[0] == default_file


def test_validation_error_branch_prints_and_raises(monkeypatch):
    cli = _make_basiccli()
    cli.default_settings = False

    # Ensure parse args helper exists and returns something
    if not hasattr(common, "_parse_args_to_nested_dict"):
        monkeypatch.setattr(common, "_parse_args_to_nested_dict", lambda remaining: {"cli": "val"})

    # Build a ValidationError instance properly using pydantic BaseModel
    class M(BaseModel):
        x: int

    # Create a real ValidationError by attempting to validate invalid data via M
    # pydantic's ValidationError is raised by model parsing; we simulate by invoking CliApp.run to raise it
    try:
        M.parse_obj({"x": "not an int"})
    except ValidationError as ve:
        exc = ve
    else:
        pytest.skip("Could not construct ValidationError")

    def fake_run(arg_type, remaining_args, **kwargs):
        raise exc

    monkeypatch.setattr(common.CliApp, "run", staticmethod(fake_run))

    with pytest.raises(RuntimeError) as re:
        cli.get_config([])
    assert "Invalid configuration. Please check the above output." in str(re.value)
    assert cli._auto_correct_shown is True


def test_settings_error_branch_prints_and_raises(monkeypatch):
    cli = _make_basiccli()
    cli.default_settings = False

    def fake_run(arg_type, remaining_args, **kwargs):
        raise SettingsError("bad settings")

    monkeypatch.setattr(common.CliApp, "run", staticmethod(fake_run))
    with pytest.raises(RuntimeError) as re:
        cli.get_config([])
    assert "Invalid command line arguments. Please check the above output in the box." in str(re.value)
    assert cli._auto_correct_shown is True


def test_print_config_prints_yaml_and_exits(monkeypatch, capsys):
    cli = _make_basiccli()
    cli.default_settings = False

    # Return a config with model_dump producing known dict
    def fake_run(arg_type, remaining_args, **kwargs):
        return DummyConfig({"a": 1, "b": {"c": 2}})

    monkeypatch.setattr(common.CliApp, "run", staticmethod(fake_run))

    with pytest.raises(SystemExit) as exc:
        cli.get_config(["--print_config"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "a:" in out and "1" in out
    assert "b:" in out and "c:" in out
