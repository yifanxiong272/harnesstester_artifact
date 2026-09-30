import types
import pytest

import sweagent.tools.utils as utils


def test_generate_command_docs_with_signature_and_docstring_round_106(monkeypatch):
    # Ensure get_signature is not used in this scenario (signatures present)
    monkeypatch.setattr(utils, "get_signature", lambda cmd: "SHOULD_NOT_BE_CALLED")

    cmd1 = types.SimpleNamespace(
        name="cmd1",
        docstring="Doc for {role}",
        signature="sig1",
        arguments=[],
    )

    arg = types.SimpleNamespace(name="x", required=True, type="int", description="an int")
    sub1 = types.SimpleNamespace(
        name="sub1",
        docstring=None,
        signature="sig_sub",
        arguments=[arg],
    )

    docs = utils.generate_command_docs([cmd1], [sub1], role="admin")

    # Assertions for cmd1 (docstring formatted and explicit signature used)
    assert "cmd1:\n" in docs
    assert "  docstring: Doc for admin\n" in docs
    assert "  signature: sig1\n" in docs

    # Assertions for sub1 (no docstring, signature present, and argument rendered)
    assert "sub1:\n" in docs
    assert "  signature: sig_sub\n" in docs
    assert "  arguments:\n" in docs
    assert "    - x (int) [required]: an int\n" in docs


def test_generate_command_docs_calls_get_signature_when_signature_missing_round_106(monkeypatch):
    calls = []

    def fake_get_signature(cmd):
        # record that get_signature was invoked with the expected command object
        calls.append(cmd.name)
        return f"computed({cmd.name})"

    monkeypatch.setattr(utils, "get_signature", fake_get_signature)

    cmd = types.SimpleNamespace(
        name="no_sig",
        docstring=None,
        signature=None,
        arguments=[],
    )

    docs = utils.generate_command_docs([cmd], [], dummy_kw=1)

    # The fallback signature from our patched get_signature should appear
    assert "no_sig:\n" in docs
    assert "  signature: computed(no_sig)\n" in docs
    # Ensure our fake_get_signature was actually called once for this command
    assert calls == ["no_sig"]
