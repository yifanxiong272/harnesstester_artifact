import types
from types import SimpleNamespace
from pr_agent.algo import file_filter
from pr_agent.algo.file_filter import filter_ignored


class _F:
    def __init__(self, filename=None, new=None, old=None):
        self.filename = filename
        self.new = new
        self.old = old


class _PathObj:
    def __init__(self, path):
        self.path = path


class _NewOld:
    def __init__(self, path):
        self.path = path


def _make_settings(regex_str, glob_str=None, ignore_language_framework=None, generated_code=None):
    # Build a settings object similar to what get_settings() is expected to return
    ignore = SimpleNamespace(regex=regex_str, glob=glob_str)
    config = {}
    if ignore_language_framework is not None:
        config['ignore_language_framework'] = ignore_language_framework
    generated_code = generated_code or {}
    return SimpleNamespace(ignore=ignore, config=config, generated_code=generated_code)


def test_platforms_round_030(monkeypatch):
    """
    Verify filtering behavior across multiple platforms (github, bitbucket, bitbucket_server,
    gitlab, azure, gitea). This drives through string->list branches for patterns and globs,
    list handling for generated_code strings, and each platform-specific branch.
    """
    # Provide patterns as a simple string so code takes the "isinstance(..., str)" branches
    settings = _make_settings(regex_str='skip', glob_str='glob_skip', ignore_language_framework=['cg1'], generated_code={'cg1': 'gen_skip'})
    # Patch get_settings and get_logger used by the module
    monkeypatch.setattr(file_filter, 'get_settings', lambda: settings)
    monkeypatch.setattr(file_filter, 'get_logger', lambda: SimpleNamespace(warning=lambda *a, **k: None))

    # 1) github: objects with .filename attribute
    files = [
        _F(filename='keep.py'),
        _F(filename='skip_file.py'),  # should be filtered out because pattern 'skip' matches
        _F(filename=None),  # falsy filename should be removed by truthy check
    ]
    out = filter_ignored(list(files), platform='github')
    # Only the object with filename 'keep.py' should remain
    assert isinstance(out, list)
    assert [getattr(f, 'filename', None) for f in out] == ['keep.py']

    # 2) bitbucket: objects with .new and .old attributes
    class New:
        def __init__(self, path):
            self.path = path

    class Old:
        def __init__(self, path):
            self.path = path

    b_files = [
        _F(new=New('keep_new.py')),              # keep
        _F(new=New('skip_new.py')),              # skip
        _F(old=Old('keep_old.py')),              # keep
        _F(old=Old('skip_old.py')),              # skip
        _F(),                                    # has neither new nor old -> ignored
    ]
    out_b = filter_ignored(list(b_files), platform='bitbucket')
    # Expect only entries with paths not matching 'skip'
    assert [getattr(f.new, 'path', getattr(f.old, 'path', None)) for f in out_b] == ['keep_new.py', 'keep_old.py']

    # 3) bitbucket_server: dicts with nested path->toString
    bs_files = [
        {'path': {'toString': 'keep_bs.py'}},
        {'path': {'toString': 'skip_bs.py'}},
        {'path': {}},  # missing toString -> should be filtered out
    ]
    out_bs = filter_ignored(list(bs_files), platform='bitbucket_server')
    assert [f['path']['toString'] for f in out_bs] == ['keep_bs.py']

    # 4) gitlab: dicts with new_path / old_path
    gl_files = [
        {'new_path': 'keep_gl_new.py'},
        {'new_path': 'skip_gl_new.py'},
        {'old_path': 'keep_gl_old.py'},
        {'old_path': 'skip_gl_old.py'},
        {'other': 'no_paths'},
    ]
    out_gl = filter_ignored(list(gl_files), platform='gitlab')
    # Keep only those with new_path/old_path that don't match 'skip'
    kept = sorted([f.get('new_path') or f.get('old_path') for f in out_gl])
    assert kept == sorted(['keep_gl_new.py', 'keep_gl_old.py'])

    # 5) azure: list of raw file path strings
    az_files = ['keep_az.py', 'skip_az.py']
    out_az = filter_ignored(list(az_files), platform='azure')
    assert out_az == ['keep_az.py']

    # 6) gitea: dicts with filename key
    gi_files = [{'filename': 'keep_gi.py'}, {'filename': 'skip_gi.py'}, {'no_filename': 'x'}]
    out_gi = filter_ignored(list(gi_files), platform='gitea')
    # Note: entries lacking 'filename' yield f.get('filename', '') -> '' which doesn't match 'skip',
    # so such entries are retained. Expect both the kept filename and a dict with no filename (None).
    assert [f.get('filename') for f in out_gi] == ['keep_gi.py', None]


def test_exception_round_030(monkeypatch):
    """
    If get_settings() raises, the function should catch the exception and return the original files.
    This covers the exception handler branch.
    """
    def _bad_get_settings():
        raise RuntimeError('boom')

    monkeypatch.setattr(file_filter, 'get_settings', _bad_get_settings)
    monkeypatch.setattr(file_filter, 'get_logger', lambda: SimpleNamespace(warning=lambda *a, **k: None))

    sample = [1, 2, 3]
    out = filter_ignored(list(sample), platform='github')
    # When settings fails, filter_ignored should return the original object unchanged (or equivalent)
    assert out == sample
