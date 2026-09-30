# file: aider/coders/base_coder.py:207-295
# asked: {"lines": [240, 241, 242, 244, 257, 258, 260, 272, 273, 277, 286, 287, 290], "branches": [[239, 240], [256, 257], [267, 277], [271, 272], [285, 286], [289, 290]]}
# gained: {"lines": [240, 241, 242, 244, 257, 258, 260, 272, 273, 277, 286, 287, 290], "branches": [[239, 240], [256, 257], [267, 277], [271, 272], [285, 286], [289, 290]]}

import types
from types import SimpleNamespace

import pytest

import aider
from aider.coders import base_coder


def make_main_model(
    *,
    name="main",
    weak_model=None,
    thinking_tokens=0,
    reasoning_effort=None,
    caches_by_default=False,
    supports_assistant_prefill=False,
    editor_name="editor",
    editor_edit_format="edfmt",
    repo_map_tokens=100,
):
    if weak_model is None:
        weak_model = SimpleNamespace(name="weak")
    info = {"supports_assistant_prefill": supports_assistant_prefill}
    editor_model = SimpleNamespace(name=editor_name)
    class MM:
        def __init__(self):
            self.name = name
            self.weak_model = weak_model
            self.caches_by_default = caches_by_default
            self.info = info
            self.editor_model = editor_model
            self.editor_edit_format = editor_edit_format

        def get_thinking_tokens(self):
            return thinking_tokens

        def get_reasoning_effort(self):
            return reasoning_effort

        def get_repo_map_tokens(self):
            return repo_map_tokens

    return MM()


def make_repo(tracked_count, rel_dir="repo/dir"):
    class R:
        def get_rel_repo_dir(self):
            return rel_dir

        def get_tracked_files(self):
            # return an actual list so len() works
            return list(range(tracked_count))

    return R()


def make_repo_map(max_map_tokens, refresh="manual"):
    return SimpleNamespace(max_map_tokens=max_map_tokens, refresh=refresh)


def make_io(multiline_mode=False):
    return SimpleNamespace(multiline_mode=multiline_mode)


def call_get_announcements(fake_self):
    # call unbound method with our fake self to avoid needing to construct a real Coder
    return base_coder.Coder.get_announcements(fake_self)


def test_get_announcements_architect_large_repo_repo_map_warning_readonly_and_done(monkeypatch):
    # ensure urls.large_repos has a known value
    monkeypatch.setattr(aider.urls, "large_repos", "http://example.com/large", raising=False)

    # weak_model different so prefix is "Main model"
    weak = SimpleNamespace(name="weak-model")
    main = make_main_model(
        name="primary",
        weak_model=weak,
        thinking_tokens=123,
        reasoning_effort="high",
        caches_by_default=True,
        supports_assistant_prefill=True,
        editor_name="ed-name",
        editor_edit_format="architect-edit",
        repo_map_tokens=100,
    )

    repo = make_repo(tracked_count=1001, rel_dir="my/repo")
    repo_map = make_repo_map(max_map_tokens=500, refresh="hourly")

    fake_self = SimpleNamespace()
    fake_self.edit_format = "architect"  # triggers editor model branch
    fake_self.main_model = main
    fake_self.add_cache_headers = False
    fake_self.repo = repo
    fake_self.repo_map = repo_map
    fake_self.get_inchat_relative_files = lambda: ["a.py"]
    fake_self.abs_read_only_fnames = ["/abs/path/file1.py"]
    fake_self.get_rel_fname = lambda _: "file1.py"
    fake_self.done_messages = True
    fake_self.io = make_io(multiline_mode=False)

    lines = call_get_announcements(fake_self)

    # Assertions for items we expect to be present
    assert any(line.startswith("Aider v") for line in lines)
    assert "Architect" not in "".join(lines)  # ensure case sensitivity isn't an issue

    # Editor model line
    assert "Editor model: ed-name with architect-edit edit format" in lines

    # Large repo warnings
    assert any("Git repo: my/repo with 1,001 files" == line for line in lines)
    assert any("Warning: For large repos" in line for line in lines)
    assert any("http://example.com/large" in line for line in lines)

    # Repo-map using tokens and warning about > max_map_tokens (max_map_tokens = main.get_repo_map_tokens()*2 = 200)
    assert any(line.startswith("Repo-map: using 500 tokens, hourly refresh") for line in lines)
    assert any("map-tokens > 200" in line for line in lines)

    # In-chat files and read-only files
    assert "Added a.py to the chat." in lines
    assert "Added file1.py to the chat (read-only)." in lines

    # Restored history
    assert "Restored previous conversation history." in lines


def test_get_announcements_repo_map_disabled_and_no_repo(monkeypatch):
    # Set large_repos to something harmless (not used here but keep consistent)
    monkeypatch.setattr(aider.urls, "large_repos", "http://example.com/large", raising=False)

    # weak_model is the same as main to get "Model" prefix
    main = make_main_model(
        name="solo",
        weak_model=None,  # factory sets different by default; force same by assignment below
        thinking_tokens=0,
        reasoning_effort=None,
        caches_by_default=False,
        supports_assistant_prefill=False,
        editor_name="ed",
        editor_edit_format="fmt",
        repo_map_tokens=50,
    )
    # make weak_model same as main
    main.weak_model = main

    fake_self = SimpleNamespace()
    fake_self.edit_format = "inline"
    fake_self.main_model = main
    fake_self.add_cache_headers = False
    fake_self.repo = None  # triggers "Git repo: none"
    fake_self.repo_map = make_repo_map(max_map_tokens=0, refresh="never")  # triggers map_tokens == 0 branch
    fake_self.get_inchat_relative_files = lambda: []
    fake_self.abs_read_only_fnames = []
    fake_self.get_rel_fname = lambda x: x  # shouldn't be used
    fake_self.done_messages = False
    fake_self.io = make_io(multiline_mode=False)

    lines = call_get_announcements(fake_self)

    assert "Git repo: none" in lines
    # Repo-map disabled because map_tokens == 0
    assert "Repo-map: disabled because map_tokens == 0" in lines
    # Editor model should NOT be present
    assert not any(line.startswith("Editor model:") for line in lines)
    # No restored conversation history
    assert not any("Restored previous conversation history." == line for line in lines)
