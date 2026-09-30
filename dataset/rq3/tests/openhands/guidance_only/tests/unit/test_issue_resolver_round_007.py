import asyncio
import os
from types import SimpleNamespace
import pathlib
import pytest

from openhands.resolver.issue_resolver import IssueResolver
import openhands.resolver.issue_resolver as issue_resolver_module

# All test functions end with _round_007 as required.

@pytest.mark.asyncio
async def test_comment_pr_no_review_round_007(tmp_path, monkeypatch):
    """When comment_id is set and issue_type == 'pr' and there are no review/thread comments,
    resolve_issue should raise a ValueError describing the missing matching comment.
    """
    # Build a bare-bones IssueResolver instance bypassing __init__
    r = IssueResolver.__new__(IssueResolver)

    # Prepare attributes used by resolve_issue
    r.comment_id = 42
    r.issue_type = 'pr'
    r.app_config = SimpleNamespace(get_llm_config=lambda: SimpleNamespace(model='some/path/model-name'))
    r.output_dir = str(tmp_path)
    r.issue_number = 123
    r.repo_instruction = None
    r.max_iterations = 1

    # issue returned by extract_issue has no review_comments, review_threads, or thread_comments
    issue = SimpleNamespace(number=123, review_comments=[], review_threads=[], thread_comments=[], head_branch='branch')
    r.extract_issue = lambda: issue

    # stub out methods/attributes used but not relevant here
    r.issue_handler = SimpleNamespace(get_clone_url=lambda: 'https://example.com/repo.git')
    async def dummy_process_issue(issue_obj, base_commit, issue_handler, reset_logger):
        return SimpleNamespace(model_dump_json=lambda: '{}')
    r.process_issue = dummy_process_issue

    # Ensure repo does not interfere: create repo dir so clone is skipped (not needed for this branch)
    repo_dir = os.path.join(r.output_dir, 'repo')
    pathlib.Path(repo_dir).mkdir(parents=True, exist_ok=True)

    # Patch subprocess.check_output to return a deterministic commit hash for later calls
    monkeypatch.setattr(issue_resolver_module.subprocess, 'check_output', lambda *args, **kwargs: b'abc123\n')

    with pytest.raises(ValueError) as excinfo:
        await r.resolve_issue(reset_logger=False)

    assert f'Comment ID {r.comment_id} did not have a match for issue {issue.number}' in str(excinfo.value)


@pytest.mark.asyncio
async def test_comment_issue_no_thread_round_007(tmp_path, monkeypatch):
    """When comment_id is set and issue_type == 'issue' and there are no thread_comments,
    resolve_issue should raise a ValueError describing the missing matching comment.
    """
    r = IssueResolver.__new__(IssueResolver)
    r.comment_id = 99
    r.issue_type = 'issue'
    r.app_config = SimpleNamespace(get_llm_config=lambda: SimpleNamespace(model='x/y-model'))
    r.output_dir = str(tmp_path)
    r.issue_number = 999
    r.repo_instruction = None
    r.max_iterations = 1

    # issue with empty thread_comments to trigger the branch
    issue = SimpleNamespace(number=999, thread_comments=[])
    r.extract_issue = lambda: issue

    r.issue_handler = SimpleNamespace(get_clone_url=lambda: 'https://example.com/repo.git')
    async def dummy_process_issue(issue_obj, base_commit, issue_handler, reset_logger):
        return SimpleNamespace(model_dump_json=lambda: '{}')
    r.process_issue = dummy_process_issue

    # Make sure there's a repo dir so clone isn't invoked
    pathlib.Path(os.path.join(r.output_dir, 'repo')).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(issue_resolver_module.subprocess, 'check_output', lambda *a, **k: b'commit-hash\n')

    with pytest.raises(ValueError) as excinfo:
        await r.resolve_issue(reset_logger=True)

    assert f'Comment ID {r.comment_id} did not have a match for issue {issue.number}' in str(excinfo.value)


@pytest.mark.asyncio
async def test_clone_fatal_raises_round_007(tmp_path, monkeypatch):
    """If cloning the repository yields output containing 'fatal', resolve_issue should raise RuntimeError.
    This exercises the branch where subprocess.check_output returns a fatal error message during clone.
    """
    r = IssueResolver.__new__(IssueResolver)
    r.comment_id = None
    r.issue_type = 'issue'
    r.app_config = SimpleNamespace(get_llm_config=lambda: SimpleNamespace(model='some/model'))
    r.output_dir = str(tmp_path)
    r.issue_number = 7
    r.repo_instruction = None
    r.max_iterations = 1

    # extract_issue returns a minimal issue object
    issue = SimpleNamespace(number=7, thread_comments=['c'])
    r.extract_issue = lambda: issue

    r.issue_handler = SimpleNamespace(get_clone_url=lambda: 'https://example.com/nonexistent.git')

    # Patch subprocess.check_output so that the clone command returns a fatal error
    def fake_check_output(cmd, cwd=None, **kwargs):
        # emulate git clone returning a fatal string
        if cmd[:2] == ['git', 'clone']:
            return b"fatal: repository 'https://example.com/nonexistent.git' not found"
        # other git commands won't be reached in this test, but return something safe
        return b'default'

    monkeypatch.setattr(issue_resolver_module.subprocess, 'check_output', fake_check_output)

    # Ensure repo dir does not exist so clone path is taken
    repo_dir = os.path.join(r.output_dir, 'repo')
    if os.path.exists(repo_dir):
        # remove if created by prior tests
        for _ in range(3):
            try:
                os.rmdir(repo_dir)
            except Exception:
                break

    with pytest.raises(RuntimeError) as excinfo:
        await r.resolve_issue(reset_logger=False)

    assert 'Failed to clone repository' in str(excinfo.value)


@pytest.mark.asyncio
async def test_pr_branch_none_round_007(tmp_path, monkeypatch):
    """When issue_type == 'pr' but head_branch is falsy, resolve_issue should raise ValueError('Branch name cannot be None').
    This also ensures the code path that checks out PR branches reaches the branch-name validation.
    """
    r = IssueResolver.__new__(IssueResolver)
    r.comment_id = None
    r.issue_type = 'pr'
    r.app_config = SimpleNamespace(get_llm_config=lambda: SimpleNamespace(model='a/b'))
    r.output_dir = str(tmp_path)
    r.issue_number = 55
    r.repo_instruction = None
    r.max_iterations = 2

    # issue has head_branch set to None to trigger branch-name None error
    issue = SimpleNamespace(number=55, head_branch=None, thread_comments=['x'])
    r.extract_issue = lambda: issue

    r.issue_handler = SimpleNamespace(get_clone_url=lambda: 'https://example.com/repo.git')

    # Create repo dir to skip cloning
    repo_dir = os.path.join(r.output_dir, 'repo')
    pathlib.Path(repo_dir).mkdir(parents=True, exist_ok=True)

    # Provide a deterministic rev-parse response
    def fake_check_output(cmd, cwd=None, **kwargs):
        # if asking for rev-parse, return a commit
        if cmd[:2] == ['git', 'rev-parse']:
            return b'feedface\n'
        return b''

    monkeypatch.setattr(issue_resolver_module.subprocess, 'check_output', fake_check_output)

    # Make sure no pre-existing output file will cause an early return
    output_file = os.path.join(r.output_dir, 'output.jsonl')
    if os.path.exists(output_file):
        os.remove(output_file)

    with pytest.raises(ValueError) as excinfo:
        await r.resolve_issue(reset_logger=False)

    assert 'Branch name cannot be None' in str(excinfo.value)
