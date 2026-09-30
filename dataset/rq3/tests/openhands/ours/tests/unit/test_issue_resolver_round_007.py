import asyncio
import os
import subprocess
from types import SimpleNamespace
import pathlib
import json
import pytest

from openhands.resolver import issue_resolver
from openhands.resolver.issue_resolver import IssueResolver


class DummyLLM:
    def __init__(self, model: str):
        self.model = model


class DummyAppConfig:
    def __init__(self, model: str = "provider/some-model"):
        self._llm = DummyLLM(model)

    def get_llm_config(self):
        return self._llm


class DummyIssueHandler:
    def __init__(self, clone_url: str = "git://example/repo.git"):
        self._url = clone_url

    def get_clone_url(self):
        return self._url


# Helper to build a resolver instance without running __init__
def make_resolver(instance_overrides: dict):
    r = object.__new__(IssueResolver)
    # Set reasonable defaults
    r.app_config = DummyAppConfig()
    r.output_dir = instance_overrides.get("output_dir", str(pathlib.Path("/tmp/irrel") / ("out")))
    r.issue_handler = instance_overrides.get("issue_handler", DummyIssueHandler())
    r.repo_instruction = instance_overrides.get("repo_instruction", None)
    r.issue_type = instance_overrides.get("issue_type", "issue")
    r.comment_id = instance_overrides.get("comment_id", None)
    r.issue_number = instance_overrides.get("issue_number", 1)
    r.max_iterations = instance_overrides.get("max_iterations", 1)
    r.process_issue = instance_overrides.get("process_issue", None)
    r.extract_issue = instance_overrides.get("extract_issue", lambda: SimpleNamespace(number=r.issue_number, review_comments=True, review_threads=True, thread_comments=True, head_branch="branch"))
    return r


def test_comment_id_missing_match_raises_ValueError_round_007(tmp_path):
    """If a comment_id is provided but the issue has no matching review/thread comments, a ValueError is raised.

    This exercises the early comment-id validation branches at the start of resolve_issue.
    """
    resolver = make_resolver({
        "output_dir": str(tmp_path / "out1"),
        "comment_id": "C123",
        "issue_type": "pr",
    })

    # Provide an issue with no comments to trigger the specific ValueError branch
    resolver.extract_issue = lambda: SimpleNamespace(
        number=42, review_comments=False, review_threads=False, thread_comments=False, head_branch="x"
    )

    with pytest.raises(ValueError) as exc:
        asyncio.run(resolver.resolve_issue(reset_logger=False))

    # Assert the message references the comment id and issue number to ensure the branch was taken
    assert "Comment ID" in str(exc.value) and "42" in str(exc.value)


def test_clone_fatal_raises_RuntimeError_round_007(tmp_path, monkeypatch):
    """When git clone returns output containing 'fatal', resolve_issue should raise a RuntimeError.

    This targets the clone -> fatal -> RuntimeError branch.
    """
    out_dir = tmp_path / "out_clone"
    resolver = make_resolver({
        "output_dir": str(out_dir),
        "comment_id": None,
        "issue_type": "issue",
        "issue_number": 7,
    })

    # Ensure output dir doesn't exist so the code attempts to clone
    if out_dir.exists():
        # cleanup if necessary
        for _ in out_dir.iterdir():
            pass

    # Provide a simple issue; clone fails before deeper usage
    resolver.extract_issue = lambda: SimpleNamespace(number=7)

    # Patch subprocess.check_output so that the clone command returns a fatal-containing byte string
    def fake_check_output(args, cwd=None):
        # detect clone invocation
        if isinstance(args, (list, tuple)) and len(args) >= 2 and args[0] == "git" and args[1] == "clone":
            return b"fatal: repository not found"
        # default safe reply
        return b""

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    with pytest.raises(RuntimeError) as exc:
        asyncio.run(resolver.resolve_issue(reset_logger=False))

    assert "Failed to clone repository" in str(exc.value)


def test_early_skip_when_output_contains_issue_round_007(tmp_path, monkeypatch):
    """If output.jsonl already contains the issue number, resolve_issue should return early (skip processing).

    This exercises the output-file existence loop and early return branch.
    """
    out_dir = tmp_path / "out_skip"
    repo_dir = out_dir / "repo"
    repo_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    resolver = make_resolver({
        "output_dir": str(out_dir),
        "comment_id": None,
        "issue_type": "issue",
        "issue_number": 99,
    })

    # Ensure app config model parsing runs deterministically
    resolver.app_config = DummyAppConfig("provider/interesting-model")

    # Prepare an output file that includes an entry matching issue_number
    output_file = out_dir / "output.jsonl"
    # The actual content does not matter because we'll patch model_validate_json
    output_file.write_text("{\"dummy\": true}\n")

    # Patch ResolverOutput.model_validate_json to return a structure with matching issue number
    def fake_model_validate_json(line):
        return SimpleNamespace(issue=SimpleNamespace(number=99))

    monkeypatch.setattr(issue_resolver.ResolverOutput, "model_validate_json", staticmethod(fake_model_validate_json))

    # Patch subprocess.check_output for the rev-parse call to return a commit id
    def fake_check_output(args, cwd=None):
        if isinstance(args, (list, tuple)) and args[:2] == ["git", "rev-parse"]:
            return b"deadbeef\n"
        return b""

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    # Call resolve_issue - it should return early without raising
    result = asyncio.run(resolver.resolve_issue(reset_logger=False))

    assert result is None
