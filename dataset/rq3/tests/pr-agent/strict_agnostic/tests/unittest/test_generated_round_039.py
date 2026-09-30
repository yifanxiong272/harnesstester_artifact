import os
from pr_agent.git_providers.git_provider import get_git_ssl_env
import pr_agent.git_providers.git_provider as gp

class DummyLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []

    def info(self, msg, **kwargs):
        # store the message and any artifact kwargs for inspection
        self.infos.append((msg, kwargs))

    def warning(self, msg, **kwargs):
        self.warnings.append((msg, kwargs))


def test_ssl_cert_exists_and_mismatch_round_039(tmp_path, monkeypatch):
    # Create three distinct cert files so that mismatch logic triggers
    ssl_file = tmp_path / "ssl.pem"
    ssl_file.write_text("ssl")
    req_file = tmp_path / "req.pem"
    req_file.write_text("req")
    git_file = tmp_path / "git.pem"
    git_file.write_text("git")

    # Set environment to point to these files
    monkeypatch.setenv("SSL_CERT_FILE", str(ssl_file))
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(req_file))
    monkeypatch.setenv("GIT_SSL_CAINFO", str(git_file))

    # Replace the module logger with our deterministic dummy logger
    dummy = DummyLogger()
    monkeypatch.setattr(gp, "get_logger", lambda: dummy)

    returned = get_git_ssl_env()

    # The function should prefer SSL_CERT_FILE and set both GIT_SSL_CAINFO and REQUESTS_CA_BUNDLE to it
    assert returned["GIT_SSL_CAINFO"] == str(ssl_file)
    assert returned["REQUESTS_CA_BUNDLE"] == str(ssl_file)

    # The mismatch among the three variables should have produced a warning
    assert any("Found mismatch" in msg for msg, _ in dummy.warnings)


def test_requests_ca_bundle_exists_no_git_ssl_round_039(tmp_path, monkeypatch):
    # Ensure SSL_CERT_FILE is not set to force fallback to REQUESTS_CA_BUNDLE
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("GIT_SSL_CAINFO", raising=False)

    req_file = tmp_path / "req2.pem"
    req_file.write_text("req2")
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(req_file))

    dummy = DummyLogger()
    monkeypatch.setattr(gp, "get_logger", lambda: dummy)

    returned = get_git_ssl_env()

    # REQUESTS_CA_BUNDLE should be chosen and both keys set to it
    assert returned["GIT_SSL_CAINFO"] == str(req_file)
    assert returned["REQUESTS_CA_BUNDLE"] == str(req_file)

    # The code path using REQUESTS_CA_BUNDLE should have produced an info log
    assert any("REQUESTS_CA_BUNDLE" in msg or "Using SSL certificate bundle from REQUESTS_CA_BUNDLE" in msg for msg, _ in dummy.infos)


def test_none_set_round_039(monkeypatch):
    # Clear relevant environment variables to simulate none defined
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("GIT_SSL_CAINFO", raising=False)

    dummy = DummyLogger()
    monkeypatch.setattr(gp, "get_logger", lambda: dummy)

    returned = get_git_ssl_env()

    # No SSL keys should be injected when none are defined
    assert "GIT_SSL_CAINFO" not in returned
    assert "REQUESTS_CA_BUNDLE" not in returned

    # The function should warn that no SSL configuration was found
    assert any("Neither SSL_CERT_FILE" in msg or "not found" in msg or "defined" in msg for msg, _ in dummy.warnings)
