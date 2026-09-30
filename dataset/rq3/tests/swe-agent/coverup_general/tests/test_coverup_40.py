# file: sweagent/utils/config.py:60-80
# asked: {"lines": [69, 71, 75, 76, 77, 78, 79, 80], "branches": [[65, 75], [68, 69], [70, 71], [75, 76], [75, 78], [79, 0], [79, 80]]}
# gained: {"lines": [69, 71, 75, 76, 77, 78, 79, 80], "branches": [[65, 75], [68, 69], [70, 71], [75, 76], [75, 78], [79, 0], [79, 80]]}

import logging
from pathlib import Path

import pytest

from sweagent.utils import config as config_module


def test_load_from_cwd_env_file_logs_info(tmp_path, monkeypatch, caplog):
    # Arrange: create a .env file in a fake cwd
    fake_cwd = tmp_path / "cwd"
    fake_cwd.mkdir()
    env_file = fake_cwd / ".env"
    env_file.write_text("KEY=VALUE")

    # Ensure REPO_ROOT points somewhere without .env so cwd branch is taken
    monkeypatch.setattr(config_module, "REPO_ROOT", tmp_path / "repo_noenv")

    # Monkeypatch Path.cwd used inside the module to return our fake cwd
    monkeypatch.setattr(config_module.Path, "cwd", classmethod(lambda cls: fake_cwd))

    # Spy on load_dotenv to ensure it's called and return True to trigger logging.info
    calls = []

    def fake_load_dotenv(dotenv_path):
        calls.append(dotenv_path)
        return True

    monkeypatch.setattr(config_module, "load_dotenv", fake_load_dotenv)

    # Act
    caplog.set_level(logging.INFO)
    config_module.load_environment_variables(None)

    # Assert: load_dotenv was called with the cwd .env file and info was logged
    assert calls == [env_file]
    assert f"Loaded environment variables from {env_file}" in caplog.text


def test_load_from_repo_env_file_no_info_when_nothing_loaded(tmp_path, monkeypatch, caplog):
    # Arrange: create a repository with .env but cwd without .env
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    repo_env = repo_dir / ".env"
    repo_env.write_text("FOO=BAR")

    fake_cwd = tmp_path / "cwd2"
    fake_cwd.mkdir()

    # Monkeypatch cwd and REPO_ROOT so repo branch is taken
    monkeypatch.setattr(config_module.Path, "cwd", classmethod(lambda cls: fake_cwd))
    monkeypatch.setattr(config_module, "REPO_ROOT", repo_dir)

    # Spy on load_dotenv and return False to avoid info logging
    calls = []

    def fake_load_dotenv(dotenv_path):
        calls.append(dotenv_path)
        return False

    monkeypatch.setattr(config_module, "load_dotenv", fake_load_dotenv)

    # Act
    caplog.set_level(logging.INFO)
    config_module.load_environment_variables(None)

    # Assert: load_dotenv was called with the repo .env file and no info log about loading
    assert calls == [repo_env]
    assert f"Loaded environment variables from {repo_env}" not in caplog.text


def test_path_not_file_raises_file_not_found(tmp_path):
    # Arrange: create a directory and pass it as path (is_file will be False)
    dir_path = tmp_path / "not_a_file"
    dir_path.mkdir()

    # Act & Assert: should raise FileNotFoundError with path in message
    with pytest.raises(FileNotFoundError) as excinfo:
        config_module.load_environment_variables(dir_path)

    assert str(dir_path) in str(excinfo.value)
