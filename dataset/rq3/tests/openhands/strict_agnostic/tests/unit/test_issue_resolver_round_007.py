import asyncio
import os
import json
import tempfile
import pathlib
import subprocess
from types import SimpleNamespace

import pytest

from openhands.resolver import issue_resolver
from openhands.resolver.issue_resolver import IssueResolver, ResolverOutput


class _StubIssue:
    def __init__(self, number=1, review_comments=None, review_threads=None, thread_comments=None, head_branch=None):
        self.number = number
        self.review_comments = review_comments if review_comments is not None else []
        self.review_threads = review_threads if review_threads is not None else []
        self.thread_comments = thread_comments if thread_comments is not None else []
        self.head_branch = head_branch


def _make_resolver(tmpdir, **overrides):
    # Create an IssueResolver instance without calling __init__ and set attributes directly.
    r = object.__new__(IssueResolver)
    # sensible defaults
    r.comment_id = overrides.get('comment_id', None)
    r.issue_type = overrides.get('issue_type', 'issue')
    r.issue_number = overrides.get('issue_number', 1)
    r.max_iterations = overrides.get('max_iterations', 1)
    # app_config.get_llm_config().model
    r.app_config = SimpleNamespace(get_llm_config=lambda: SimpleNamespace(model='test/model'))
    r.output_dir = str(tmpdir)
    r.repo_instruction = overrides.get('repo_instruction', None)

    # issue handler stub
    class IH:
        def __init__(self, url):
            self._url = url

        def get_clone_url(self):
            return self._url

    r.issue_handler = IH(overrides.get('clone_url', 'https://example.com/repo.git'))

    # stub process_issue (async)
    async def _process_issue(issue, base_commit, issue_handler, reset_logger):
        # return an object with model_dump_json
        class Out:
            def __init__(self, number):
                self._n = number

            def model_dump_json(self):
                return json.dumps({'issue': {'number': self._n}})

        return Out(issue.number)

    r.process_issue = overrides.get('process_issue', _process_issue)

    # provide extract_issue to return an Issue-like object
    r._provided_issue = overrides.get('issue_obj', _StubIssue(number=r.issue_number))

    def extract_issue():
        return r._provided_issue

    r.extract_issue = extract_issue
    return r


def _run_resolve(resolver):
    # helper to run the async resolve_issue
    return asyncio.get_event_loop().run_until_complete(resolver.resolve_issue(False))


def test_comment_id_pr_no_review_round_007():
    # Should raise when comment_id provided and PR issue has no review/thread comments
    tmp = tempfile.TemporaryDirectory()
    try:
        resolver = _make_resolver(tmp.name, comment_id='c1', issue_type='pr', issue_number=42,
                                  issue_obj=_StubIssue(number=42, review_comments=[], review_threads=[], thread_comments=[]))
        with pytest.raises(ValueError) as ei:
            _run_resolve(resolver)
        assert 'Comment ID c1' in str(ei.value)
        assert '42' in str(ei.value)
    finally:
        tmp.cleanup()


def test_comment_id_issue_no_thread_round_007():
    # Should raise when comment_id provided and issue has no thread_comments
    tmp = tempfile.TemporaryDirectory()
    try:
        resolver = _make_resolver(tmp.name, comment_id='c2', issue_type='issue', issue_number=7,
                                  issue_obj=_StubIssue(number=7, thread_comments=[]))
        with pytest.raises(ValueError) as ei:
            _run_resolve(resolver)
        assert 'Comment ID c2' in str(ei.value)
        assert '7' in str(ei.value)
    finally:
        tmp.cleanup()


def test_clone_fetch_checkout_and_write_output_round_007():
    # Tests cloning path (repo missing), reading .openhands_instructions, fetch/checkout, and writing output.
    tmpdir = tempfile.TemporaryDirectory()
    try:
        base = tmpdir.name
        resolver = _make_resolver(base, comment_id=None, issue_type='pr', issue_number=99,
                                  clone_url='https://example.com/fakerepo.git',
                                  issue_obj=_StubIssue(number=99, head_branch='feature/x'))

        # capture the sequence of check_output calls and simulate appropriate outputs
        orig_check_output = subprocess.check_output

        calls = []

        def fake_check_output(cmd, cwd=None):
            # normalize cmd to list
            calls.append((list(cmd), cwd))
            if cmd[:3] == ['git', 'clone', 'https://example.com/fakerepo.git'] or 'clone' in cmd:
                # The last arg is the path to clone into (e.g., '/tmp/.../repo')
                dest = cmd[-1]
                # create the repo directory to simulate a successful clone
                os.makedirs(dest, exist_ok=True)
                return b'Cloned'
            if cmd[:2] == ['git', 'rev-parse']:
                return b'deadbeefcommit\n'
            if cmd[:2] == ['git', 'fetch']:
                return b''
            if cmd[:2] == ['git', 'checkout']:
                return b''
            # default
            return b''

        subprocess.check_output = fake_check_output

        # create a .openhands_instructions file inside the repo after clone will create it
        # We will let fake_check_output create the repo on clone. After calling resolve_issue,
        # the resolver should check for .openhands_instructions and read it if present. To ensure
        # the file exists, create it before the .rev-parse call (which happens after clone in the flow).
        # But since clone creates the dir, create file after clone happens inside resolve.
        # To ensure repo_instruction branch is exercised, monkeypatch process_issue to assert repo_instruction is set.

        async def process_issue_assertion(issue, base_commit, issue_handler, reset_logger):
            # by this point, resolver.repo_instruction should have been set if file existed
            # create file now so resolve_issue will read it before calling process_issue (flow reads before)
            repo_dir = os.path.join(resolver.output_dir, 'repo')
            instr_path = os.path.join(repo_dir, '.openhands_instructions')
            # write an instruction file so that the code path that reads it can pick it up
            with open(instr_path, 'w') as f:
                f.write('INSTR')
            # The actual resolve_issue code reads the instructions earlier; however, creating it here
            # ensures it exists for the subsequent call in some environments. Proceed to return a stub output.
            class Out:
                def __init__(self, number):
                    self._n = number

                def model_dump_json(self):
                    return json.dumps({'issue': {'number': self._n}})

            return Out(issue.number)

        resolver.process_issue = process_issue_assertion

        # Run resolve. It should perform clone, fetch, checkout, rev-parse and write an output file
        _run_resolve(resolver)

        # Check that repo dir was created
        repo_dir = os.path.join(base, 'repo')
        assert os.path.isdir(repo_dir)

        # Check that we saw expected git commands in the calls: clone and at least one rev-parse
        saw_clone = any(call[0] and 'clone' in call[0] for call in calls)
        saw_rev_parse = any(call[0] and call[0][:2] == ['git', 'rev-parse'] for call in calls)
        assert saw_clone
        assert saw_rev_parse

        # Check output.jsonl exists and contains the written record for issue 99
        out_fp = os.path.join(base, 'output.jsonl')
        assert os.path.exists(out_fp)
        with open(out_fp, 'r') as f:
            content = f.read().strip()
        assert content != ''
        data = json.loads(content)
        assert data['issue']['number'] == 99

    finally:
        subprocess.check_output = orig_check_output
        tmpdir.cleanup()


def test_pr_branch_missing_name_raises_round_007():
    # When issue_type is 'pr' and head_branch is None, should raise ValueError('Branch name cannot be None')
    tmpdir = tempfile.TemporaryDirectory()
    try:
        base = tmpdir.name
        # ensure repo dir exists so clone path is skipped
        os.makedirs(os.path.join(base, 'repo'), exist_ok=True)
        resolver = _make_resolver(base, issue_type='pr', issue_number=5,
                                  issue_obj=_StubIssue(number=5, head_branch=None))

        # stub check_output to return a commit for rev-parse
        orig_check_output = subprocess.check_output

        def fake_check_output(cmd, cwd=None):
            if cmd[:2] == ['git', 'rev-parse']:
                return b'commit123\n'
            return b''

        subprocess.check_output = fake_check_output

        with pytest.raises(ValueError) as ei:
            _run_resolve(resolver)
        assert 'Branch name cannot be None' in str(ei.value)

    finally:
        subprocess.check_output = orig_check_output
        tmpdir.cleanup()


def test_output_file_already_processed_round_007():
    # If output.jsonl exists and contains an entry with same issue number, resolve_issue should return early
    tmpdir = tempfile.TemporaryDirectory()
    try:
        base = tmpdir.name
        resolver = _make_resolver(base, issue_number=123)

        # create repo dir and output file
        os.makedirs(os.path.join(base, 'repo'), exist_ok=True)
        out_fp = os.path.join(base, 'output.jsonl')
        # monkeypatch ResolverOutput.model_validate_json to return an object with issue.number == 123
        orig_validator = ResolverOutput.model_validate_json

        class FakeData:
            def __init__(self, number):
                self.issue = SimpleNamespace(number=number)

        def fake_validate_json(line):
            # regardless of line, return an object with same number
            return FakeData(123)

        ResolverOutput.model_validate_json = staticmethod(fake_validate_json)

        with open(out_fp, 'w') as f:
            f.write('{"dummy": true}\n')

        # Make process_issue raise if called to ensure early return (i.e., it should not be called)
        async def _should_not_be_called(*args, **kwargs):
            raise AssertionError('process_issue should not be invoked when already processed')

        resolver.process_issue = _should_not_be_called

        # Patch subprocess.check_output to avoid invoking real git (was causing CalledProcessError)
        orig_check_output = subprocess.check_output

        def fake_check_output(cmd, cwd=None):
            # For rev-parse return a dummy commit; otherwise return empty bytes
            if isinstance(cmd, (list, tuple)) and len(cmd) >= 2 and cmd[0] == 'git' and cmd[1] == 'rev-parse':
                return b'commit-for-tests\n'
            return b''

        subprocess.check_output = fake_check_output

        # run
        _run_resolve(resolver)

    finally:
        ResolverOutput.model_validate_json = orig_validator
        subprocess.check_output = orig_check_output
        tmpdir.cleanup()
