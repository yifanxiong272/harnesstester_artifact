import os
import pytest

from opendevin.action import fileop


def test_resolve_path_leading_slash_after_trim_preserves_workspace_base(monkeypatch):
    """
    Boundary surface: leading-slash-after-trim causing os.path.join to ignore WORKSPACE_BASE
    Ensure that when SANDBOX_PATH_PREFIX has no trailing slash and the trimmed remainder begins with '/',
    the returned path still preserves the WORKSPACE_BASE as a prefix.
    """
    base = '/workspace/base'
    # SANDBOX_PATH_PREFIX without trailing slash to produce a leading '/' in the remainder
    monkeypatch.setattr(fileop, 'SANDBOX_PATH_PREFIX', '/sandbox')
    # deterministically control config.get
    monkeypatch.setattr(fileop.config, 'get', lambda k: base)

    # Input that will be trimmed to '/subdir/file.txt' (leading slash remains)
    inp = '/sandbox/subdir/file.txt'
    result = fileop.resolve_path(inp)

    # Primary oracle: the returned path must preserve the workspace base as a prefix
    assert os.path.normpath(result).startswith(os.path.normpath(base)), (
        f"WORKSPACE_BASE must be preserved as prefix; got {result!r}, expected to start with {base!r}"
    )
