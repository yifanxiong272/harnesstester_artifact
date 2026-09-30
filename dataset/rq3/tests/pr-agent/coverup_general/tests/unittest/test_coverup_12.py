# file: pr_agent/git_providers/gitlab_provider.py:395-477
# asked: {"lines": [405, 406, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 421, 422, 424, 425, 426, 427, 428, 429, 430, 433, 434, 435, 436, 438, 439, 440, 441, 444, 445, 447, 448, 449, 450, 451, 452, 453, 455, 456, 457, 458, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 476, 477], "branches": [[405, 406], [405, 409], [413, 414], [413, 424], [427, 428], [427, 473], [428, 429], [428, 433], [434, 435], [434, 438], [438, 439], [438, 440], [448, 449], [448, 450], [450, 451], [450, 452], [452, 453], [452, 455], [457, 458], [457, 462], [473, 474], [473, 476]]}
# gained: {"lines": [405, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 421, 422, 424, 425, 426, 427, 428, 429, 430, 433, 434, 435, 436, 438, 439, 440, 441, 444, 445, 447, 448, 449, 450, 452, 455, 456, 457, 458, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 476, 477], "branches": [[405, 409], [413, 414], [427, 428], [427, 473], [428, 429], [428, 433], [434, 435], [434, 438], [438, 439], [448, 449], [448, 450], [450, 452], [452, 455], [457, 458], [457, 462], [473, 474]]}

import types
from types import SimpleNamespace

import pytest

import pr_agent.git_providers.gitlab_provider as glmod
from pr_agent.algo.types import EDIT_TYPE


def make_diff(old_path, new_path, diff, new_file=False, deleted_file=False, renamed_file=False):
    return {
        'old_path': old_path,
        'new_path': new_path,
        'diff': diff,
        'new_file': new_file,
        'deleted_file': deleted_file,
        'renamed_file': renamed_file,
    }


def _bind_get_pr_file_content(provider, mapping=None):
    # mapping: path -> (old/new) content prefix
    if mapping is None:
        mapping = {}

    def _get_pr_file_content(file_path, branch):
        # return bytes to ensure decode_if_bytes is used
        prefix = mapping.get(file_path, "content")
        return f"{prefix}:{file_path}@{branch}".encode('utf-8')

    provider.get_pr_file_content = types.MethodType(lambda self, p, b: _get_pr_file_content(p, b), provider)


def test_get_diff_files_main_flow(monkeypatch):
    # Make MAX small to hit the threshold branch
    monkeypatch.setattr(glmod, 'MAX_FILES_ALLOWED_FULL', 2)

    # Prepare diffs_original: first is invalid file, then three valid ones
    diffs_original = [
        make_diff('bad.tmp', 'bad.tmp', '+++ some', new_file=False),
        make_diff('a.py', 'a.py', '+line\n-line\n', new_file=False),
        make_diff('b.py', 'b.py', '+added\n', new_file=False),
        make_diff('c_old.py', 'c_new.py', '', new_file=True, renamed_file=True),
    ]

    # filter_ignored will return same elements but different order to trigger the logging about filtering
    diffs_filtered = [diffs_original[1], diffs_original[2], diffs_original[3], diffs_original[0]]

    # Create a fake MR object
    mr = SimpleNamespace()
    mr.changes = lambda: {'changes': diffs_original}
    mr.diff_refs = {'base_sha': 'base123', 'head_sha': 'head123'}

    # Create provider instance without calling __init__
    provider = object.__new__(glmod.GitLabProvider)
    provider.diff_files = None
    provider.mr = mr
    provider.id_mr = 42
    provider.pr_url = "http://gitlab/mock/42"

    # Monkeypatch filter_ignored to our reorder function
    monkeypatch.setattr(glmod, 'filter_ignored', lambda diffs, src: diffs_filtered)

    # is_valid_file: return False only for 'bad.tmp'
    def is_valid_file(path):
        return not path.endswith('.tmp')

    monkeypatch.setattr(glmod, 'is_valid_file', is_valid_file)

    # decode_if_bytes: decode bytes to str
    monkeypatch.setattr(glmod, 'decode_if_bytes', lambda v: v.decode('utf-8') if isinstance(v, (bytes, bytearray)) else v)

    # load_large_diff should be called for the file with empty diff ('c_new.py'), return a sample patch
    monkeypatch.setattr(glmod, 'load_large_diff', lambda filename, new_content, old_content: "+new_line_in_large\n-old_line_in_large\n")

    # Prepare get_pr_file_content to return bytes for any path
    _bind_get_pr_file_content(provider)

    # Create a dummy logger to capture info messages
    logged = []
    class DummyLogger:
        def info(self, msg, extra=None):
            logged.append((msg, extra))

    monkeypatch.setattr(glmod, 'get_logger', lambda: DummyLogger())

    # Run get_diff_files and validate outputs
    diff_files = glmod.GitLabProvider.get_diff_files(provider)

    # We expect 3 valid diff files (bad.tmp filtered out by is_valid_file)
    assert isinstance(diff_files, list)
    assert len(diff_files) == 3

    filenames = [f.filename for f in diff_files]
    assert 'a.py' in filenames
    assert 'b.py' in filenames
    assert 'c_new.py' in filenames

    # Verify edit types: 'c_new.py' was new_file=True -> ADDED
    for f in diff_files:
        if f.filename == 'c_new.py':
            assert f.edit_type == EDIT_TYPE.ADDED
        else:
            assert f.edit_type == EDIT_TYPE.MODIFIED

    # Verify plus/minus line counts are computed from patches (load_large_diff for c_new.py)
    for f in diff_files:
        if f.filename == 'a.py':
            assert f.num_plus_lines >= 1
        if f.filename == 'c_new.py':
            # load_large_diff returned 1 plus and 1 minus line
            assert f.num_plus_lines == 1
            assert f.num_minus_lines == 1

    # Provider should cache diff_files
    assert provider.diff_files is diff_files

    # Check that logger captured the filtered and invalid messages and the too-many-files log
    # There should be at least one "Filtered out" style entry and one "Filtered out files with invalid extensions"
    msgs = [m[0] for m in logged]
    assert any('Filtered out' in m for m in msgs)
    assert any('invalid extensions' in m for m in msgs)


def test_get_diff_files_handles_logger_exception(monkeypatch):
    # Test that an exception in the logger.info inside the try/except does not break processing

    monkeypatch.setattr(glmod, 'MAX_FILES_ALLOWED_FULL', 2)

    diffs_original = [
        make_diff('bad.tmp', 'bad.tmp', '+++ some', new_file=False),
        make_diff('a.py', 'a.py', '+line\n', new_file=False),
    ]
    # Force filtered to be different order to enter try block
    diffs_filtered = [diffs_original[1], diffs_original[0]]

    mr = SimpleNamespace()
    mr.changes = lambda: {'changes': diffs_original}
    mr.diff_refs = {'base_sha': 'b', 'head_sha': 'h'}

    provider = object.__new__(glmod.GitLabProvider)
    provider.diff_files = None
    provider.mr = mr
    provider.id_mr = 7
    provider.pr_url = "http://gitlab/mock/7"

    monkeypatch.setattr(glmod, 'filter_ignored', lambda diffs, src: diffs_filtered)
    monkeypatch.setattr(glmod, 'is_valid_file', lambda path: not path.endswith('.tmp'))
    monkeypatch.setattr(glmod, 'decode_if_bytes', lambda v: v.decode('utf-8') if isinstance(v, (bytes, bytearray)) else v)
    monkeypatch.setattr(glmod, 'load_large_diff', lambda filename, new_content, old_content: "+x\n-x\n")
    _bind_get_pr_file_content(provider)

    # Logger that raises on the filtered message only
    class FlakyLogger:
        def __init__(self):
            self.called = 0

        def info(self, msg, extra=None):
            # raise only for the filtered-out message
            if isinstance(msg, str) and 'Filtered out [ignore] files' in msg:
                raise RuntimeError("logger failed")
            self.called += 1

    monkeypatch.setattr(glmod, 'get_logger', lambda: FlakyLogger())

    # Should not raise despite the logger raising inside the try block
    diff_files = glmod.GitLabProvider.get_diff_files(provider)
    assert isinstance(diff_files, list)
    # bad.tmp filtered out by is_valid_file, only a.py remains
    assert len(diff_files) == 1
    assert diff_files[0].filename == 'a.py'
    assert provider.diff_files is diff_files
