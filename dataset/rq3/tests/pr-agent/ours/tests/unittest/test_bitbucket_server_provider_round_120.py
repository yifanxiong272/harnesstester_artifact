import pytest
from packaging.version import parse as parse_version

from pr_agent.git_providers import bitbucket_server_provider as bbmod
from pr_agent.git_providers.bitbucket_server_provider import BitbucketServerProvider, EDIT_TYPE


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, msg):
        self.infos.append(msg)

    def error(self, msg):
        self.errors.append(msg)


def _make_provider_instance():
    # Create a provider instance without invoking __init__ to allow precise attribute control
    prov = BitbucketServerProvider.__new__(BitbucketServerProvider)
    prov.diff_files = None
    prov.pr = {
        'fromRef': {'latestCommit': 'head123'},
        'toRef': {'latestCommit': 'tohead123'}
    }
    prov.pr_url = 'http://example/pr/1'
    prov.workspace_slug = 'ws'
    prov.repo_slug = 'repo'
    prov.pr_num = 1
    return prov


def test_return_cached_diff_files_round_120():
    # If diff_files already present, get_diff_files should return it immediately (covers line 231)
    prov = _make_provider_instance()
    sentinel = [object()]
    prov.diff_files = sentinel

    result = BitbucketServerProvider.get_diff_files(prov)
    assert result is sentinel


def test_merge_base_api_failure_round_120(monkeypatch):
    # Simulate bitbucket_api_version >= 8.16 and bitbucket_client.get raising -> logger.error and exception (covers 236-241)
    prov = _make_provider_instance()
    prov.bitbucket_api_version = parse_version("8.16")

    class FakeClient:
        def get(self, *args, **kwargs):
            raise ValueError("boom-merge-base")

    prov.bitbucket_client = FakeClient()

    logger = DummyLogger()
    monkeypatch.setattr(bbmod, 'get_logger', lambda: logger)

    with pytest.raises(ValueError):
        prov.get_diff_files()

    # Ensure the error logger was called with a helpful message containing PR url
    assert any('Failed to get the best common ancestor' in e or 'best common ancestor' in e for e in logger.errors)
    assert any(prov.pr_url in e for e in logger.errors)


def test_get_best_common_ancestor_commit_list_failure_round_120(monkeypatch):
    # Simulate api version in [7.0, 8.15] where get_commits raises -> logger.error and exception (covers 252-260)
    prov = _make_provider_instance()
    prov.bitbucket_api_version = parse_version("7.1")

    class FakeClient:
        def get_pull_requests_commits(self, workspace, repo, pr_num):
            # return an iterable where last entry has parents list with an id
            yield {'parents': [{'id': 'base123'}]}

        def get_commits(self, workspace, repo, base_sha, head_commit):
            raise RuntimeError("boom-commits")

    prov.bitbucket_client = FakeClient()

    logger = DummyLogger()
    monkeypatch.setattr(bbmod, 'get_logger', lambda: logger)

    with pytest.raises(RuntimeError):
        prov.get_diff_files()

    assert any('Failed to get the commit list for calculating best common ancestor' in e or 'calculating best common ancestor' in e for e in logger.errors)
    assert any(prov.pr_url in e for e in logger.errors)


def test_changes_handling_and_skip_non_code_round_120(monkeypatch):
    # Cover skipping non-code files and ADD, DELETE, RENAME, MODIFY branches (lines 266-293, 296-307)
    prov = _make_provider_instance()
    prov.bitbucket_api_version = None  # choose the simple-diff path (else branch)

    # Provide commits list so base_sha can be determined from last commit parent
    class FakeClient:
        def get_pull_requests_commits(self, workspace, repo, pr_num):
            yield {'parents': [{'id': 'baseABC'}]}

        def get_pull_requests_changes(self, workspace, repo, pr_num):
            # Include a non-code file first to trigger skip, then various change types
            return [
                {'path': {'toString': 'dir/README.md'}, 'type': 'MODIFY'},
                {'path': {'toString': 'src/new.py'}, 'type': 'ADD'},
                {'path': {'toString': 'src/remove.py'}, 'type': 'DELETE'},
                {'path': {'toString': 'src/rename.py'}, 'type': 'RENAME'},
                {'path': {'toString': 'src/modify.py'}, 'type': 'MODIFY'},
            ]

    prov.bitbucket_client = FakeClient()

    # filter_ignored should be used by code; return input unchanged
    monkeypatch.setattr(bbmod, 'filter_ignored', lambda changes, provider_name: list(changes))

    # is_valid_file should return False for README.md and True for .py files
    def fake_is_valid_file(name):
        return not name.lower().endswith('readme.md')

    monkeypatch.setattr(bbmod, 'is_valid_file', fake_is_valid_file)

    # get_file should return bytes depending on the commit id provided
    def fake_get_file(path, commit_id):
        if commit_id == prov.pr['fromRef']['latestCommit']:
            return b'new-content-for:' + path.encode()
        return b'old-content-for:' + path.encode()

    prov.get_file = fake_get_file

    # decode_if_bytes decodes bytes to str
    monkeypatch.setattr(bbmod, 'decode_if_bytes', lambda x: x.decode() if isinstance(x, (bytes, bytearray)) else x)

    # load_large_diff should produce a deterministic patch text for assertions
    monkeypatch.setattr(bbmod, 'load_large_diff', lambda file_path, new, orig, show_warning=False: f'PATCH:{file_path}')

    # Capture info logging to validate skip occurred
    logger = DummyLogger()
    monkeypatch.setattr(bbmod, 'get_logger', lambda: logger)

    diffs = prov.get_diff_files()

    # README.md should have been skipped, so we expect 4 entries
    assert len(diffs) == 4

    # Map paths to expected edit types
    path_to_expected = {
        'src/new.py': EDIT_TYPE.ADDED,
        'src/remove.py': EDIT_TYPE.DELETED,
        'src/rename.py': EDIT_TYPE.RENAMED,
        'src/modify.py': EDIT_TYPE.MODIFIED,
    }

    seen = {d.filepath: d for d in diffs}

    for p, expected in path_to_expected.items():
        assert p in seen
        assert seen[p].edit_type == expected
        # patch was generated deterministically
        assert seen[p].patch == f'PATCH:{p}'

    # Ensure skip of non-code file produced an info log
    assert any('Skipping a non-code file' in m or 'Skipping' in m for m in logger.infos)
