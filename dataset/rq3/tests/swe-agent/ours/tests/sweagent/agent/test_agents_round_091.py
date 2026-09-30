import types
from types import SimpleNamespace
import pytest

from sweagent.agent import agents


class FakePF:
    def __init__(self, patch, read_method=None):
        # record the provided patch for deterministic behavior
        self.patch = patch

    def get_files_str(self, original=False, context_length=0):
        # deterministic, depends only on inputs
        return f"fake:{self.patch}:{context_length}"


class RaisingPF:
    def __init__(self, *args, **kwargs):
        # mimic the real parse error raised by unidiff
        raise agents.UnidiffParseError("boom")


class CapturingLogger:
    def __init__(self):
        self.errors = []

    def error(self, msg):
        self.errors.append(msg)


def make_env_with_repo():
    # minimal env with repo and read_file used by the lambda in the code
    repo = SimpleNamespace(repo_name="myrepo")
    def read_file(path):
        # path will be a PurePosixPath; return deterministic content
        return "file-content"

    return SimpleNamespace(repo=repo, read_file=read_file)


def test_get_edited_files_with_valid_patch_pf_round_091(monkeypatch):
    """When PatchFormatter returns an object, its get_files_str result is used for each context length."""
    # Patch the module-level PatchFormatter to our deterministic FakePF
    monkeypatch.setattr(agents, "PatchFormatter", FakePF)

    fake_agent = SimpleNamespace()
    fake_agent._env = make_env_with_repo()
    fake_agent.logger = CapturingLogger()

    patch_text = "SOME PATCH"
    out = agents.DefaultAgent._get_edited_files_with_context(fake_agent, patch_text)

    # Expected keys for the three context lengths
    assert set(out.keys()) == {"edited_files30", "edited_files50", "edited_files70"}

    # Values should be produced by FakePF.get_files_str deterministically
    assert out["edited_files30"] == f"fake:{patch_text}:30"
    assert out["edited_files50"] == f"fake:{patch_text}:50"
    assert out["edited_files70"] == f"fake:{patch_text}:70"

    # No error should have been logged
    assert fake_agent.logger.errors == []


def test_get_edited_files_handles_unidiff_parse_error_round_091(monkeypatch):
    """If PatchFormatter raises UnidiffParseError, the method logs an error and returns empty-file messages."""
    # Patch to a constructor that raises the UnidiffParseError
    monkeypatch.setattr(agents, "PatchFormatter", RaisingPF)

    fake_agent = SimpleNamespace()
    fake_agent._env = make_env_with_repo()
    fake_agent.logger = CapturingLogger()

    # Provide any truthy patch so the constructor is attempted
    out = agents.DefaultAgent._get_edited_files_with_context(fake_agent, "irrelevant")

    # The exact error message from the source must be logged
    assert fake_agent.logger.errors == [
        "Failed to parse patch with unidiff. Some variables will be empty."
    ]

    # Since parsing failed, pf is None and the default message should be used
    assert out["edited_files30"] == "Empty. No edited files found."
    assert out["edited_files50"] == "Empty. No edited files found."
    assert out["edited_files70"] == "Empty. No edited files found."
