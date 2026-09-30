import base64
import types
import importlib

import pytest

from pr_agent.git_providers.gitlab_provider import GitLabProvider


class _FakeFile:
    def __init__(self, decode_value=None, decode_raises=False, content=None):
        self._decode_value = decode_value
        self._decode_raises = decode_raises
        # content is expected to be base64-encoded string by the provider logic
        self.content = content

    def decode(self):
        if self._decode_raises:
            raise Exception("decode failed")
        return self._decode_value


class _FakeProj:
    def __init__(self, files_by_ref: dict):
        # files_by_ref: mapping ref->_FakeFile or exception to raise
        self._files = files_by_ref

    class _Files:
        def __init__(self, parent):
            self._parent = parent

        def get(self, file_path=None, ref=None):
            # emulate raising if ref not found
            v = self._parent._files.get(ref, None)
            if isinstance(v, Exception):
                raise v
            return v

    @property
    def files(self):
        return _FakeProj._Files(self)


class _FakeGL:
    def __init__(self, proj):
        self.projects = types.SimpleNamespace(get=lambda id_project: proj)


def _make_provider_with(gl_obj, id_project="1", target_branch=None, source_branch=None):
    # create instance without calling __init__ to avoid external deps
    p = object.__new__(GitLabProvider)
    p.gl = gl_obj
    p.id_project = id_project
    p.mr = types.SimpleNamespace(target_branch=target_branch, source_branch=source_branch)
    return p


def test_projects_get_raises_round_099():
    # If projects.get raises, _get_gitmodules_map should return empty dict
    class BadProjects:
        def get(self, id_project):
            raise Exception("boom")

    g = types.SimpleNamespace(projects=BadProjects())
    prov = _make_provider_with(g, id_project="42", target_branch=None, source_branch=None)

    assert prov._get_gitmodules_map() == {}


def test_no_branches_returns_empty_round_099():
    # If both target_branch and source_branch are falsy, returns {}
    proj = _FakeProj(files_by_ref={})
    gl = _FakeGL(proj)
    prov = _make_provider_with(gl, id_project="1", target_branch=None, source_branch=None)

    assert prov._get_gitmodules_map() == {}


def test_decode_bytes_and_strip_quotes_round_099():
    # When File.decode() returns bytes, function should decode and parse
    raw = b'[submodule "subA"]\n\tpath = pathA\n\turl = "urlA"\n'
    fake_file = _FakeFile(decode_value=raw, decode_raises=False, content=None)
    proj = _FakeProj(files_by_ref={"target": fake_file})
    gl = _FakeGL(proj)
    prov = _make_provider_with(gl, id_project="1", target_branch="target", source_branch=None)

    out = prov._get_gitmodules_map()
    # expect pathA (no quotes) -> urlA (quotes stripped)
    assert out == {"pathA": "urlA"}


def test_decode_falls_back_to_base64_content_round_099():
    # When decode() raises, but content holds base64-encoded data, it should decode
    # Use a clearly quoted string that is valid Python source (double-quoted outer string,
    # single-quoted URL inside) to avoid syntax issues.
    content_text = "[submodule \"subB\"]\n\tpath = \"pB\"\n\turl = 'uB'\n"
    # create base64 string
    b64 = base64.b64encode(content_text.encode("utf-8")).decode("ascii")
    fake_file = _FakeFile(decode_value=None, decode_raises=True, content=b64)
    proj = _FakeProj(files_by_ref={"tbranch": fake_file})
    gl = _FakeGL(proj)
    prov = _make_provider_with(gl, id_project="1", target_branch="tbranch", source_branch=None)

    out = prov._get_gitmodules_map()
    # quotes around path/url should be stripped and outer single quotes handled
    assert out == {"pB": "uB"}


def test_parser_read_string_exception_returns_empty_round_099(monkeypatch):
    # Force configparser.ConfigParser.read_string to raise, expect empty dict
    mod = importlib.import_module("pr_agent.git_providers.gitlab_provider")

    class BadParser:
        def __init__(self, *args, **kwargs):
            pass

        def read_string(self, s):
            raise Exception("bad parse")

    # Patch the ConfigParser used in the module
    monkeypatch.setattr(mod, "configparser", types.SimpleNamespace(ConfigParser=BadParser))

    # Make a file that would otherwise be parseable
    raw = b'[submodule "x"]\n\tpath = xpath\n\turl = xurl\n'
    fake_file = _FakeFile(decode_value=raw, decode_raises=False, content=None)
    proj = _FakeProj(files_by_ref={"tb": fake_file})
    gl = _FakeGL(proj)
    prov = _make_provider_with(gl, id_project="1", target_branch="tb", source_branch=None)

    assert prov._get_gitmodules_map() == {}
