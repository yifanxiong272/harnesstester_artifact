# file: sweagent/agent/agents.py:866-893
# asked: {"lines": [883, 884, 885], "branches": []}
# gained: {"lines": [883, 884, 885], "branches": []}

import types
from types import SimpleNamespace

import pytest
from unidiff import UnidiffParseError

import sweagent.agent.agents as agents_mod


def _make_agent_with_env():
    # Create an uninitialized DefaultAgent instance and attach minimal attributes
    agent = object.__new__(agents_mod.DefaultAgent)
    # Minimal env: repo with a repo_name and a read_file method
    agent._env = SimpleNamespace(repo=SimpleNamespace(repo_name="myrepo"), read_file=lambda path: "file contents")
    # Minimal logger that records error messages
    agent._logged_errors = []
    class DummyLogger:
        def error(self, msg):
            agent._logged_errors.append(msg)
    agent.logger = DummyLogger()
    return agent


def test_get_edited_files_with_context_unidiff_parse_error(monkeypatch):
    """
    Ensure that when PatchFormatter raises UnidiffParseError during construction,
    the except block is executed, pf becomes None, an error is logged, and the
    returned dictionary contains the fallback "Empty. No edited files found." values.
    """
    agent = _make_agent_with_env()

    # Patch PatchFormatter in the module to raise UnidiffParseError when called
    def raising_patchformatter(*args, **kwargs):
        raise UnidiffParseError("invalid patch")
    monkeypatch.setattr(agents_mod, "PatchFormatter", raising_patchformatter)

    out = agent._get_edited_files_with_context("some-bad-patch")

    # Confirm the error was logged with the exact message from the code
    assert any(
        "Failed to parse patch with unidiff. Some variables will be empty." == msg
        for msg in agent._logged_errors
    ), f"Expected error log not found in {agent._logged_errors}"

    # Confirm the output fallback values are present for all three context lengths
    expected = {
        "edited_files30": "Empty. No edited files found.",
        "edited_files50": "Empty. No edited files found.",
        "edited_files70": "Empty. No edited files found.",
    }
    assert out == expected


def test_get_edited_files_with_context_uses_patchformatter_when_available(monkeypatch):
    """
    Ensure that when PatchFormatter works, its get_files_str is used to populate the outputs.
    This exercises the branch where pf is not None and avoids the exception path.
    """
    agent = _make_agent_with_env()

    # Create a fake PatchFormatter that exposes get_files_str
    class FakePF:
        def __init__(self, patch, read_method=None):
            # store patch and read_method to mimic realistic behavior
            self.patch = patch
            self.read_method = read_method

        def get_files_str(self, original: bool, context_length: int):
            return f"files({context_length}) for patch={self.patch}"

    monkeypatch.setattr(agents_mod, "PatchFormatter", FakePF)

    out = agent._get_edited_files_with_context("good-patch")

    assert out["edited_files30"] == "files(30) for patch=good-patch"
    assert out["edited_files50"] == "files(50) for patch=good-patch"
    assert out["edited_files70"] == "files(70) for patch=good-patch"
