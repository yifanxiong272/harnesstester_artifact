# file: openhands/resolver/issue_resolver.py:549-679
# asked: {"lines": [560, 562, 563, 564, 565, 567, 568, 571, 572, 573, 577, 579, 580, 581, 583, 586, 587, 588, 589, 590, 591, 592, 593, 595, 596, 597, 600, 601, 602, 603, 605, 607, 609, 610, 612, 613, 614, 617, 618, 621, 622, 623, 624, 625, 626, 627, 629, 631, 633, 634, 637, 639, 640, 641, 642, 645, 646, 649, 650, 651, 652, 656, 657, 658, 659, 662, 663, 664, 665, 668, 669, 670, 671, 672, 674, 675, 678, 679], "branches": [[560, 561], [560, 577], [561, 567], [561, 571], [571, 572], [571, 577], [587, 588], [587, 600], [596, 597], [596, 600], [607, 609], [607, 617], [612, 613], [612, 617], [621, 622], [621, 631], [623, 624], [623, 631], [625, 623], [625, 626], [639, 640], [639, 668], [645, 646], [645, 649]]}
# gained: {"lines": [560, 562, 563, 564, 565, 567, 568, 571, 572, 573, 577, 579, 580, 581, 583, 586, 587, 600, 601, 602, 603, 605, 607, 609, 610, 612, 613, 614, 617, 618, 621, 631, 633, 634, 637, 639, 640, 641, 642, 645, 646, 649, 650, 651, 652, 656, 657, 658, 659, 662, 663, 664, 665, 668, 669, 670, 671, 672, 674, 675, 678, 679], "branches": [[560, 561], [560, 577], [561, 567], [561, 571], [571, 572], [587, 600], [607, 609], [612, 613], [621, 631], [639, 640], [645, 646], [645, 649]]}

import asyncio
import os
import pathlib
import subprocess
from types import SimpleNamespace
import pytest
from openhands.resolver.issue_resolver import IssueResolver

@pytest.mark.asyncio
async def test_comment_id_pr_no_match_raises():
    # Setup a dummy self with minimal attrs to trigger the PR comment-id mismatch
    dummy = SimpleNamespace()
    dummy.comment_id = 123
    dummy.issue_type = 'pr'
    # extract_issue returns an issue with no review comments/threads
    dummy.extract_issue = lambda: SimpleNamespace(number=42, review_comments=[], review_threads=[], thread_comments=[])
    # Call the coroutine and assert ValueError is raised with expected message
    with pytest.raises(ValueError) as exc:
        await IssueResolver.resolve_issue(dummy)  # calling unbound coroutine with dummy self
    assert f'Comment ID {dummy.comment_id} did not have a match for issue 42' in str(exc.value)

@pytest.mark.asyncio
async def test_comment_id_issue_no_thread_comments_raises():
    # Setup dummy for issue type (not PR) with no thread_comments
    dummy = SimpleNamespace()
    dummy.comment_id = 'cid-xyz'
    dummy.issue_type = 'issue'
    dummy.extract_issue = lambda: SimpleNamespace(number=7, thread_comments=[])
    with pytest.raises(ValueError) as exc:
        await IssueResolver.resolve_issue(dummy)
    assert f'Comment ID {dummy.comment_id} did not have a match for issue 7' in str(exc.value)

@pytest.mark.asyncio
async def test_resolve_issue_pr_branch_none_creates_output_file_and_closes(tmp_path, monkeypatch):
    # Setup output dir and repo dir
    outdir = tmp_path / "outdir_branch_none"
    outdir.mkdir()
    repo_dir = outdir / "repo"
    repo_dir.mkdir()
    # create .openhands_instructions to be read
    (repo_dir / ".openhands_instructions").write_text("repo instruction content")

    # Dummy instance attributes
    dummy = SimpleNamespace()
    dummy.comment_id = None
    dummy.issue_type = 'pr'
    dummy.issue_number = 11
    dummy.output_dir = str(outdir)
    # app_config.get_llm_config().model used to compute model_name
    dummy.app_config = SimpleNamespace(get_llm_config=lambda: SimpleNamespace(model='org/some-model'))
    dummy.max_iterations = 1
    dummy.issue_handler = SimpleNamespace(get_clone_url=lambda: 'git@github.com:owner/repo.git')
    # Provide repo_instruction attribute so resolve_issue can check and potentially read file
    dummy.repo_instruction = None
    # extract_issue returns PR with no branch -> should raise "Branch name cannot be None"
    dummy.extract_issue = lambda: SimpleNamespace(number=11, head_branch=None, review_comments=[], review_threads=[], thread_comments=[])
    # process_issue shouldn't be called, but provide a stub
    async def _proc(issue, base_commit, issue_handler, reset_logger):
        return SimpleNamespace(model_dump_json=lambda: '{"ok": true}')
    dummy.process_issue = _proc

    # Monkeypatch subprocess.check_output to always return a commit for rev-parse calls
    def fake_check_output(cmd, cwd=None):
        # emulate 'git rev-parse HEAD' returning a commit SHA
        if isinstance(cmd, (list, tuple)) and 'rev-parse' in cmd:
            return b'commitsha123\n'
        return b''
    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    # Now call and expect ValueError for missing branch
    with pytest.raises(ValueError) as exc:
        await IssueResolver.resolve_issue(dummy)
    assert 'Branch name cannot be None' in str(exc.value)

    # Confirm that output file was created (opened in append mode before try) and is closed/empty
    output_file = outdir / "output.jsonl"
    assert output_file.exists()
    # File should be empty because process_issue was not reached and nothing was written
    assert output_file.read_text() == ""

@pytest.mark.asyncio
async def test_resolve_issue_pr_checkout_and_write_success(tmp_path, monkeypatch):
    outdir = tmp_path / "outdir_success"
    outdir.mkdir()
    repo_dir = outdir / "repo"
    repo_dir.mkdir()

    # Create .openhands_instructions to cover reading branch
    (repo_dir / ".openhands_instructions").write_text("instr-success")

    dummy = SimpleNamespace()
    dummy.comment_id = None
    dummy.issue_type = 'pr'
    dummy.issue_number = 99
    dummy.output_dir = str(outdir)
    dummy.app_config = SimpleNamespace(get_llm_config=lambda: SimpleNamespace(model='org/used-model'))
    dummy.max_iterations = 2
    dummy.issue_handler = SimpleNamespace(get_clone_url=lambda: 'git@github.com:owner/repo.git')
    # Provide repo_instruction attribute so resolve_issue can read the file
    dummy.repo_instruction = None
    # extract_issue returns an issue with a branch to checkout
    dummy.extract_issue = lambda: SimpleNamespace(number=99, head_branch='feature/xyz', review_comments=[], review_threads=[], thread_comments=[])

    # Prepare an async process_issue that returns an object with model_dump_json
    async def fake_process_issue(issue, base_commit, issue_handler, reset_logger):
        # assert we receive the issue and base_commit strings
        assert issue.number == 99
        assert isinstance(base_commit, str)
        return SimpleNamespace(model_dump_json=lambda: '{"result":"written","issue":{"number":99}}')
    dummy.process_issue = fake_process_issue

    # Monkeypatch subprocess.check_output to behave differently on calls:
    # - first rev-parse -> initial commit
    # - fetch/checkout -> empty bytes
    # - second rev-parse -> new commit
    call_state = {"rev_count": 0}
    def fake_check_output(cmd, cwd=None):
        # cmd is a list like ['git','rev-parse','HEAD'] or ['git','fetch',...]
        if isinstance(cmd, (list, tuple)) and 'rev-parse' in cmd:
            call_state["rev_count"] += 1
            if call_state["rev_count"] == 1:
                return b'initial-commit\n'
            return b'new-commit\n'
        # For fetch/checkout/clone emulate success
        return b''

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    # Run resolver - should complete without exception
    await IssueResolver.resolve_issue(dummy)

    # Validate that output.jsonl now contains the written JSON line
    output_file = outdir / "output.jsonl"
    assert output_file.exists()
    content = output_file.read_text()
    # Expect exactly one line with the JSON we returned
    assert content.strip() == '{"result":"written","issue":{"number":99}}'
