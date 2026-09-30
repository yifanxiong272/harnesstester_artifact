import asyncio
import os
import json
from types import SimpleNamespace
import pathlib
import subprocess
import builtins
import pytest

from argparse import Namespace
from openhands.resolver.issue_resolver import IssueResolver
from openhands.integrations.service_types import ProviderType
from openhands.resolver import issue_resolver
from openhands.resolver import issue_resolver as ir_mod


class FakeIssue:
    def __init__(self, number=1, review_comments=None, review_threads=None, thread_comments=None, head_branch=None):
        self.number = number
        self.review_comments = review_comments if review_comments is not None else []
        self.review_threads = review_threads if review_threads is not None else []
        self.thread_comments = thread_comments if thread_comments is not None else []
        self.head_branch = head_branch


class FakeOutput:
    def __init__(self, data):
        self._data = data

    def model_dump_json(self):
        return json.dumps(self._data)


class DummyFactory:
    def __init__(self, *args, **kwargs):
        pass

    def create(self):
        # Return a minimal issue_handler with get_clone_url used in tests
        return SimpleNamespace(get_clone_url=lambda: "https://example.com/repo.git")


def make_args(tmp_path, selected_repo="owner/repo", prompt_contents="PROMPT", conversation_contents="CONV", issue_type="issue"):
    # create prompt files
    prompt_file = tmp_path / "prompt.jinja"
    prompt_file.write_text(prompt_contents)
    conv_file = tmp_path / "prompt-conversation-instructions.jinja"
    conv_file.write_text(conversation_contents)

    args = Namespace()
    args.selected_repo = selected_repo
    args.token = "fake-token"
    args.username = "fake-user"
    args.base_domain = None
    args.repo_instruction_file = None
    args.prompt_file = str(prompt_file)
    args.output_dir = str(tmp_path)
    args.issue_type = issue_type
    args.prompt_template = None
    args.max_iterations = 1
    args.runtime_container_image = None
    args.base_container_image = None
    args.is_experimental = False
    args.comment_id = None
    args.issue_number = 1
    args.runtime = None
    return args


@pytest.mark.asyncio
async def test_comment_id_pr_no_comments_round_007(tmp_path, monkeypatch):
    """When a comment_id is provided for a PR but there are no matching review/thread comments, a ValueError is raised."""
    args = make_args(tmp_path, issue_type="pr")
    # Ensure identify_token returns a known provider to avoid async network calls
    monkeypatch.setattr(ir_mod, "call_async_from_sync", lambda *a, **k: ProviderType.GITHUB)
    # Prevent IssueHandlerFactory from performing external actions
    monkeypatch.setattr(issue_resolver, "IssueHandlerFactory", DummyFactory)

    resolver = IssueResolver(args)
    # set a comment id and ensure extract_issue yields an issue with no comments
    resolver.comment_id = "c1"

    fake_issue = FakeIssue(number=42, review_comments=[], review_threads=[], thread_comments=[], head_branch="branch")
    monkeypatch.setattr(resolver, "extract_issue", lambda: fake_issue)

    with pytest.raises(ValueError) as excinfo:
        await resolver.resolve_issue(reset_logger=False)
    assert "did not have a match for issue" in str(excinfo.value)


@pytest.mark.asyncio
async def test_issue_type_issue_comment_id_no_thread_comments_round_007(tmp_path, monkeypatch):
    """When a comment_id is provided for an 'issue' but there are no thread_comments, ValueError is raised."""
    args = make_args(tmp_path, issue_type="issue")
    monkeypatch.setattr(ir_mod, "call_async_from_sync", lambda *a, **k: ProviderType.GITHUB)
    monkeypatch.setattr(issue_resolver, "IssueHandlerFactory", DummyFactory)

    resolver = IssueResolver(args)
    resolver.comment_id = "c2"

    fake_issue = FakeIssue(number=99, review_comments=[1], review_threads=[1], thread_comments=[])
    fake_issue.thread_comments = []
    monkeypatch.setattr(resolver, "extract_issue", lambda: fake_issue)

    with pytest.raises(ValueError) as excinfo:
        await resolver.resolve_issue(reset_logger=False)
    assert "did not have a match for issue" in str(excinfo.value)


@pytest.mark.asyncio
async def test_clone_fatal_raises_runtimeerror_round_007(tmp_path, monkeypatch):
    """If git clone produces a fatal error string, RuntimeError is raised and contains the clone output."""
    args = make_args(tmp_path, issue_type="issue")
    monkeypatch.setattr(ir_mod, "call_async_from_sync", lambda *a, **k: ProviderType.GITHUB)
    monkeypatch.setattr(issue_resolver, "IssueHandlerFactory", DummyFactory)

    resolver = IssueResolver(args)
    resolver.issue_handler = SimpleNamespace(get_clone_url=lambda: "https://example.com/repo.git")
    resolver.issue_number = 1

    # Ensure extract_issue returns a normal issue so we get to clone step
    fake_issue = FakeIssue(number=1)
    monkeypatch.setattr(resolver, "extract_issue", lambda: fake_issue)

    # Ensure repo dir does not exist so clone is attempted
    repo_dir = pathlib.Path(resolver.output_dir) / "repo"
    if repo_dir.exists():
        # remove to force clone path
        for p in repo_dir.rglob('*'):
            try:
                p.unlink()
            except Exception:
                pass
        try:
            repo_dir.rmdir()
        except Exception:
            pass

    # Patch subprocess.check_output to simulate 'git clone' producing fatal message
    def fake_check_output(args_list, cwd=None):
        # if this is the clone command, return a fatal message
        if isinstance(args_list, list) and len(args_list) >= 2 and args_list[0] == "git" and args_list[1] == "clone":
            return b"fatal: repository not found"
        # fallback for other git commands
        return b""

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    with pytest.raises(RuntimeError) as excinfo:
        await resolver.resolve_issue(reset_logger=False)
    assert "Failed to clone repository" in str(excinfo.value)


@pytest.mark.asyncio
async def test_pr_branch_none_raises_valueerror_round_007(tmp_path, monkeypatch):
    """If issue_type is 'pr' but head_branch is None, a ValueError about branch name is raised."""
    args = make_args(tmp_path, issue_type="pr")
    monkeypatch.setattr(ir_mod, "call_async_from_sync", lambda *a, **k: ProviderType.GITHUB)
    monkeypatch.setattr(issue_resolver, "IssueHandlerFactory", DummyFactory)

    resolver = IssueResolver(args)
    resolver.issue_handler = SimpleNamespace(get_clone_url=lambda: "https://example.com/repo.git")
    resolver.issue_number = 5

    # Create a repo dir to skip clone
    repo_dir = pathlib.Path(resolver.output_dir) / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Return a valid base commit for initial rev-parse
    def fake_check_output(args_list, cwd=None):
        if isinstance(args_list, list) and len(args_list) >= 2 and args_list[0] == "git" and args_list[1] == "rev-parse":
            return b"abcd1234\n"
        return b""

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    # Make extract_issue return an issue with head_branch None which should trigger the branch-name ValueError
    fake_issue = FakeIssue(number=5, head_branch=None)
    monkeypatch.setattr(resolver, "extract_issue", lambda: fake_issue)

    with pytest.raises(ValueError) as excinfo:
        await resolver.resolve_issue(reset_logger=False)
    assert "Branch name cannot be None" in str(excinfo.value)


@pytest.mark.asyncio
async def test_output_already_processed_returns_early_round_007(tmp_path, monkeypatch):
    """If output.jsonl already contains an entry for this issue number, resolve_issue returns early (skips processing)."""
    args = make_args(tmp_path, issue_type="issue")
    monkeypatch.setattr(ir_mod, "call_async_from_sync", lambda *a, **k: ProviderType.GITHUB)
    monkeypatch.setattr(issue_resolver, "IssueHandlerFactory", DummyFactory)

    resolver = IssueResolver(args)
    resolver.issue_handler = SimpleNamespace(get_clone_url=lambda: "https://example.com/repo.git")
    resolver.issue_number = 123

    # create repo dir to skip clone
    repo_dir = pathlib.Path(resolver.output_dir) / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    # make git rev-parse return a commit id
    def fake_check_output(args_list, cwd=None):
        if isinstance(args_list, list) and len(args_list) >= 2 and args_list[0] == "git" and args_list[1] == "rev-parse":
            return b"commit-sha-1\n"
        return b""

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    # Create output file with a line; monkeypatch ResolverOutput.model_validate_json to return an object with matching issue number
    output_file = pathlib.Path(resolver.output_dir) / "output.jsonl"
    output_file.write_text("line-1\n")

    called = {"validated": False}

    def fake_model_validate_json(line):
        called["validated"] = True
        return SimpleNamespace(issue=SimpleNamespace(number=123))

    monkeypatch.setattr(issue_resolver, "ResolverOutput", SimpleNamespace(model_validate_json=fake_model_validate_json))

    # stub extract_issue so method progresses to the output file check
    monkeypatch.setattr(resolver, "extract_issue", lambda: FakeIssue(number=123))

    # Call resolve_issue - it should return None (early return) and not raise
    result = await resolver.resolve_issue(reset_logger=False)
    assert result is None
    assert called["validated"] is True
