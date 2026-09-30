import re
from types import SimpleNamespace
import pytest

from pr_agent.algo import file_filter as ff


class _Obj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_github_and_invalid_regex_round_030(monkeypatch):
    """Exercise: string regex input branch, translate_globs_to_regexes providing invalid pattern, and logger warning when code generators config is a string.

    Expectations:
    - get_logger().warning is called when ignore_language_framework is a string.
    - invalid regex returned from translate_globs_to_regexes is ignored (no exception escapes) and valid patterns still filter files.
    """
    # Capture logger.warning call
    logger = SimpleNamespace()
    logger.warned = False

    def _warning(msg):
        logger.warned = True
        logger.last = msg

    logger.warning = _warning

    # Settings: ignore.regex as a string (triggers conversion to list)
    settings = SimpleNamespace(
        ignore=SimpleNamespace(regex="ignore", glob=[]),
        config={"ignore_language_framework": "notalist"},
        generated_code={}
    )

    # translate_globs_to_regexes returns an invalid regex to trigger the re.error path
    monkeypatch.setattr(ff, "get_settings", lambda: settings)
    monkeypatch.setattr(ff, "get_logger", lambda: logger)
    monkeypatch.setattr(ff, "translate_globs_to_regexes", lambda globs: ["(invalid["])

    files = [SimpleNamespace(filename="keep.py"), SimpleNamespace(filename="some_ignore.py")]

    out = ff.filter_ignored(files)

    # logger warning must have been called due to config being a string
    assert logger.warned is True

    # Only the non-matching filename should remain
    assert isinstance(out, list)
    assert len(out) == 1
    assert hasattr(out[0], "filename") and out[0].filename == "keep.py"


def test_platforms_round_030(monkeypatch):
    """Exercise multiple platform-specific branches: bitbucket, bitbucket_server, gitlab, azure, gitea.

    Also exercise the code path where ignore_language_framework is a list and generated_code entries are strings
    (so glob_patterns is string -> converted to list), and translate_globs_to_regexes producing usable regexes.
    """
    logger = SimpleNamespace()
    logger.warned = False

    def _warning(msg):
        logger.warned = True
        logger.last = msg

    logger.warning = _warning

    # Settings: provide a base regex that will match exactly 'match_this' and a language framework that returns a string glob
    settings = SimpleNamespace(
        ignore=SimpleNamespace(regex=["match_this"], glob=[]),
        config={"ignore_language_framework": ["cg1"]},
        generated_code={"cg1": "gen*"},
    )

    monkeypatch.setattr(ff, "get_settings", lambda: settings)
    monkeypatch.setattr(ff, "get_logger", lambda: logger)

    # translate_globs_to_regexes will translate incoming globs to regex strings.
    def translate(globs):
        out = []
        for g in globs:
            if g == "gen*":
                out.append(r"^gen.*$")
            else:
                # the main ignore pattern we expect in settings
                out.append(r"^match_this$")
        return out

    monkeypatch.setattr(ff, "translate_globs_to_regexes", translate)

    # 1) bitbucket: objects with .new and .old (attributes may be None)
    class NewOld:
        def __init__(self, new=None, old=None):
            self.new = SimpleNamespace(path=new) if new is not None else None
            self.old = SimpleNamespace(path=old) if old is not None else None

    files_bb = [NewOld(new="keep_path"), NewOld(new="match_this"), NewOld(old="old_keep")]
    out_bb = ff.filter_ignored(files_bb, platform="bitbucket")

    # Expect match_this removed, keep_path and old_keep to remain
    out_paths = []
    for f in out_bb:
        p = None
        if getattr(f, "new", None):
            p = f.new.path
        if not p and getattr(f, "old", None):
            p = f.old.path
        out_paths.append(p)

    assert "keep_path" in out_paths
    assert "old_keep" in out_paths
    assert "match_this" not in out_paths

    # 2) bitbucket_server: dicts with nested path.toString
    files_bbs = [{"path": {"toString": "match_this"}}, {"path": {"toString": "keep"}}]
    out_bbs = ff.filter_ignored(files_bbs, platform="bitbucket_server")
    assert any(item.get("path", {}).get("toString") == "keep" for item in out_bbs)
    assert all(item.get("path", {}).get("toString") != "match_this" for item in out_bbs)

    # 3) gitlab: dicts with new_path/old_path
    files_gl = [{"new_path": "keep"}, {"old_path": "match_this"}, {"old_path": "other"}]
    out_gl = ff.filter_ignored(files_gl, platform="gitlab")
    # keep should be present; match_this removed
    assert any(d.get("new_path") == "keep" for d in out_gl)
    assert all(d.get("old_path") != "match_this" for d in out_gl)

    # 4) azure: list of plain strings
    files_az = ["keep_file", "match_this", "genfile"]
    out_az = ff.filter_ignored(files_az, platform="azure")
    assert "keep_file" in out_az
    assert "match_this" not in out_az

    # 5) gitea: dicts with filename key
    files_gt = [{"filename": "keep"}, {"filename": "match_this"}, {}]
    out_gt = ff.filter_ignored(files_gt, platform="gitea")
    # keep present, match_this filtered out, empty filename treated as '' and won't match '^match_this$' so included
    assert any((item.get("filename", "") == "keep") or item == {} for item in out_gt)
    assert all(item.get("filename", "") != "match_this" for item in out_gt)
