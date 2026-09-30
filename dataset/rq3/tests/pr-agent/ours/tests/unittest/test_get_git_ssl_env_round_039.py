import importlib
import os
from types import SimpleNamespace
import pytest

from pr_agent.git_providers import git_provider
from pr_agent.git_providers.git_provider import get_git_ssl_env


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []

    def info(self, msg, **kwargs):
        # record message and kwargs for assertions
        self.infos.append((msg, kwargs))

    def warning(self, msg, **kwargs):
        self.warnings.append((msg, kwargs))


def _patch_exists(monkeypatch, existing_paths):
    """Patch the os.path.exists used by the module-under-test.

    existing_paths: set of paths that should be considered to exist.
    """
    def _exists(path):
        return path in existing_paths

    monkeypatch.setattr(git_provider.os.path, "exists", _exists)


def _fresh_logger(monkeypatch):
    logger = DummyLogger()
    # get_logger() should return our dummy logger
    monkeypatch.setattr(git_provider, "get_logger", lambda: logger)
    return logger


def test_ssl_cert_conflict_round_039(monkeypatch):
    # SSL_CERT_FILE exists and differs from REQUESTS_CA_BUNDLE and GIT_SSL_CAINFO -> warning branch
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("GIT_SSL_CAINFO", raising=False)

    monkeypatch.setenv("SSL_CERT_FILE", "/tmp/ssl_a.pem")
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "/tmp/ssl_b.pem")
    monkeypatch.setenv("GIT_SSL_CAINFO", "/tmp/ssl_c.pem")

    _patch_exists(monkeypatch, {"/tmp/ssl_a.pem"})
    logger = _fresh_logger(monkeypatch)

    returned = get_git_ssl_env()

    # chosen_cert_file should be SSL_CERT_FILE and both env vars updated
    assert returned["GIT_SSL_CAINFO"] == "/tmp/ssl_a.pem"
    assert returned["REQUESTS_CA_BUNDLE"] == "/tmp/ssl_a.pem"

    # logger.warning should be called for mismatch and include artifact with values
    assert len(logger.warnings) >= 1
    # find warning that contains our artifact dict
    found = False
    for msg, kwargs in logger.warnings:
        artifact = kwargs.get("artifact")
        if artifact and artifact.get("ssl_cert_file") == "/tmp/ssl_a.pem":
            found = True
            # ensure other artifact values are present (may be None or strings)
            assert artifact["requests_ca_bundle"] == "/tmp/ssl_b.pem"
            assert artifact["git_ssl_ca_info"] == "/tmp/ssl_c.pem"
    assert found


def test_ssl_cert_only_round_039(monkeypatch):
    # Only SSL_CERT_FILE set and exists -> info branch
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("GIT_SSL_CAINFO", raising=False)

    monkeypatch.setenv("SSL_CERT_FILE", "/tmp/solo.pem")

    _patch_exists(monkeypatch, {"/tmp/solo.pem"})
    logger = _fresh_logger(monkeypatch)

    returned = get_git_ssl_env()

    assert returned["GIT_SSL_CAINFO"] == "/tmp/solo.pem"
    assert returned["REQUESTS_CA_BUNDLE"] == "/tmp/solo.pem"

    # info should have been called indicating using SSL certificate bundle
    assert any("Using SSL certificate bundle" in msg for msg, _ in logger.infos)


def test_ssl_cert_not_found_round_039(monkeypatch):
    # SSL_CERT_FILE set but file does not exist -> warning and no chosen cert
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("GIT_SSL_CAINFO", raising=False)

    monkeypatch.setenv("SSL_CERT_FILE", "/nonexistent.pem")

    _patch_exists(monkeypatch, set())
    logger = _fresh_logger(monkeypatch)

    returned = get_git_ssl_env()

    # since chosen_cert_file is empty, returned env should not have GIT_SSL_CAINFO set to that path
    assert returned.get("GIT_SSL_CAINFO") != "/nonexistent.pem"
    assert returned.get("REQUESTS_CA_BUNDLE") != "/nonexistent.pem"

    # warning about not found should be recorded
    assert any("not found for git operations" in msg for msg, _ in logger.warnings)


def test_requests_ca_conflict_round_039(monkeypatch):
    # No SSL_CERT_FILE, REQUESTS_CA_BUNDLE exists and differs from GIT_SSL_CAINFO -> warning branch
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("GIT_SSL_CAINFO", raising=False)

    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "/tmp/req_a.pem")
    monkeypatch.setenv("GIT_SSL_CAINFO", "/tmp/req_b.pem")

    _patch_exists(monkeypatch, {"/tmp/req_a.pem"})
    logger = _fresh_logger(monkeypatch)

    returned = get_git_ssl_env()

    assert returned["GIT_SSL_CAINFO"] == "/tmp/req_a.pem"
    assert returned["REQUESTS_CA_BUNDLE"] == "/tmp/req_a.pem"

    # warning about mismatch between REQUESTS_CA_BUNDLE and GIT_SSL_CAINFO
    assert any("REQUESTS_CA_BUNDLE" in msg or ("REQUESTS_CA_BUNDLE" in kwargs.get("artifact", {})) for msg, kwargs in logger.warnings)


def test_requests_ca_only_round_039(monkeypatch):
    # REQUESTS_CA_BUNDLE exists and GIT_SSL_CAINFO absent -> info branch
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("GIT_SSL_CAINFO", raising=False)

    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "/tmp/req_only.pem")

    _patch_exists(monkeypatch, {"/tmp/req_only.pem"})
    logger = _fresh_logger(monkeypatch)

    returned = get_git_ssl_env()

    assert returned["GIT_SSL_CAINFO"] == "/tmp/req_only.pem"
    assert returned["REQUESTS_CA_BUNDLE"] == "/tmp/req_only.pem"

    assert any("REQUESTS_CA_BUNDLE" in msg for msg, _ in logger.infos)


def test_git_ssl_ca_round_039(monkeypatch):
    # Neither SSL_CERT_FILE nor REQUESTS_CA_BUNDLE set, but GIT_SSL_CAINFO exists -> info branch
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("GIT_SSL_CAINFO", raising=False)

    monkeypatch.setenv("GIT_SSL_CAINFO", "/tmp/git_ca.pem")

    _patch_exists(monkeypatch, {"/tmp/git_ca.pem"})
    logger = _fresh_logger(monkeypatch)

    returned = get_git_ssl_env()

    assert returned["GIT_SSL_CAINFO"] == "/tmp/git_ca.pem"
    assert returned["REQUESTS_CA_BUNDLE"] == "/tmp/git_ca.pem"

    assert any("Using git SSL CA info" in msg for msg, _ in logger.infos)


def test_none_defined_round_039(monkeypatch):
    # No related env vars set -> final warning and no SSL settings added
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("GIT_SSL_CAINFO", raising=False)

    _patch_exists(monkeypatch, set())
    logger = _fresh_logger(monkeypatch)

    # Ensure environment at call time is a clean copy for predictable returned_env
    returned = get_git_ssl_env()

    # No SSL keys should be force-added
    assert "GIT_SSL_CAINFO" not in returned or returned.get("GIT_SSL_CAINFO") == os.environ.get("GIT_SSL_CAINFO")
    assert "REQUESTS_CA_BUNDLE" not in returned or returned.get("REQUESTS_CA_BUNDLE") == os.environ.get("REQUESTS_CA_BUNDLE")

    # final general warning should be emitted
    assert any("Neither SSL_CERT_FILE" in msg for msg, _ in logger.warnings)
