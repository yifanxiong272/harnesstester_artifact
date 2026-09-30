# file: aider/coders/base_coder.py:207-295
# asked: {"lines": [240, 241, 242, 244, 257, 258, 260, 272, 273, 277, 286, 287, 290], "branches": [[239, 240], [256, 257], [267, 277], [271, 272], [285, 286], [289, 290]]}
# gained: {"lines": [240, 241, 242, 244, 257, 258, 260, 272, 273, 277, 286, 287, 290], "branches": [[239, 240], [256, 257], [267, 277], [271, 272], [285, 286], [289, 290]]}

import types
import builtins
import pytest

from aider.coders.base_coder import Coder
from aider import urls


class DummyModel:
    def __init__(
        self,
        name="main",
        weak_model=None,
        editor_model=None,
        editor_edit_format="diff",
        thinking_tokens=0,
        reasoning_effort=None,
        caches_by_default=False,
        supports_assistant_prefill=False,
        repo_map_tokens=0,
    ):
        self.name = name
        self.weak_model = weak_model or self
        self.editor_model = editor_model or types.SimpleNamespace(name="editor")
        self.editor_edit_format = editor_edit_format
        self._thinking_tokens = thinking_tokens
        self._reasoning_effort = reasoning_effort
        self.caches_by_default = caches_by_default
        self.info = {"supports_assistant_prefill": supports_assistant_prefill}
        self._repo_map_tokens = repo_map_tokens

    def get_thinking_tokens(self):
        return self._thinking_tokens

    def get_reasoning_effort(self):
        return self._reasoning_effort

    def get_repo_map_tokens(self):
        return self._repo_map_tokens


class DummyRepo:
    def __init__(self, rel_dir="repo/dir", tracked_files_count=0):
        self._rel_dir = rel_dir
        self._tracked_files_count = tracked_files_count

    def get_rel_repo_dir(self):
        return self._rel_dir

    def get_tracked_files(self):
        return [f"f{i}.py" for i in range(self._tracked_files_count)]


class DummyRepoMap:
    def __init__(self, max_map_tokens=0, refresh="daily"):
        self.max_map_tokens = max_map_tokens
        self.refresh = refresh


class DummyIO:
    def __init__(self, multiline_mode=False):
        self.multiline_mode = multiline_mode


def make_coder_instance():
    # Create an uninitialized Coder instance and allow tests to set attributes.
    return object.__new__(Coder)


def test_architect_editor_and_large_repo_and_repo_map_warning():
    coder = make_coder_instance()

    # main and weak models (different to trigger "Weak model" line)
    weak = DummyModel(name="weak")
    main = DummyModel(
        name="main-model",
        weak_model=weak,
        editor_model=types.SimpleNamespace(name="super-editor"),
        editor_edit_format="architect-edit",
        thinking_tokens=42,
        reasoning_effort="high",
        caches_by_default=True,
        supports_assistant_prefill=True,
        repo_map_tokens=100,
    )
    main.weak_model = weak  # ensure weak is different

    # repo with many files to trigger the large repo warning branch
    repo = DummyRepo(rel_dir="my/repo", tracked_files_count=1500)

    # repo_map with tokens greater than max_map_tokens (max_map_tokens = main.get_repo_map_tokens()*2 = 200)
    repo_map = DummyRepoMap(max_map_tokens=300, refresh="hourly")

    # set coder attributes
    coder.main_model = main
    coder.edit_format = "architect"  # triggers editor model lines
    coder.add_cache_headers = False
    coder.repo = repo
    coder.repo_map = repo_map

    # in-chat files
    coder.get_inchat_relative_files = lambda: ["added_file.py"]
    coder.abs_read_only_fnames = ["/abs/path/README.md"]
    coder.get_rel_fname = lambda fname: fname.split("/")[-1]

    coder.done_messages = True
    coder.io = DummyIO(multiline_mode=True)

    lines = coder.get_announcements()

    # Assertions check presence of expected lines
    assert any("Aider v" in l for l in lines)
    # main model line includes edit format
    assert any("Model" in l or "Main model" in l for l in lines)
    # editor model line present because edit_format == "architect"
    assert any("Editor model: super-editor with architect-edit edit format" == l for l in lines)
    # weak model line present
    assert any(l == "Weak model: weak" for l in lines)
    # repo info present with formatted number
    assert any("Git repo: my/repo with 1,500 files" == l for l in lines)
    # large repo warnings present
    assert any("Warning: For large repos, consider using --subtree-only and .aiderignore" == l for l in lines)
    assert any(l.startswith("See: ") and urls.large_repos in l for l in lines)
    # repo-map using line present
    assert any("Repo-map: using 300 tokens, hourly refresh" == l for l in lines)
    # map tokens warning present (max_map_tokens = 200)
    assert any("Warning: map-tokens > 200 is not recommended" in l for l in lines)
    # in-chat file and read-only file lines present
    assert any("Added added_file.py to the chat." == l for l in lines)
    assert any("Added README.md to the chat (read-only)." == l for l in lines)
    # restored conversation and multiline mode lines
    assert any("Restored previous conversation history." == l for l in lines)
    assert any("Multiline mode: Enabled. Enter inserts newline, Alt-Enter submits text" == l for l in lines)


def test_repo_none_and_repo_map_disabled_and_model_same_and_no_done_messages():
    coder = make_coder_instance()

    # main model where weak_model is the same (to trigger "Model" prefix and no "Weak model" line)
    main = DummyModel(
        name="solo-model",
        weak_model=None,  # will be set to self in constructor
        thinking_tokens=0,
        reasoning_effort=None,
        caches_by_default=False,
        supports_assistant_prefill=False,
        repo_map_tokens=10,
    )
    main.weak_model = main

    # repo is None to get "Git repo: none"
    repo = None

    # repo_map exists but has map_tokens == 0 to trigger disabled because map_tokens == 0
    repo_map = DummyRepoMap(max_map_tokens=0, refresh="never")
    repo_map.max_map_tokens = 0

    coder.main_model = main
    coder.edit_format = "normal"
    coder.add_cache_headers = False
    coder.repo = repo
    coder.repo_map = repo_map

    coder.get_inchat_relative_files = lambda: []
    coder.abs_read_only_fnames = []
    coder.get_rel_fname = lambda fname: fname  # not used here

    coder.done_messages = False
    coder.io = DummyIO(multiline_mode=False)

    lines = coder.get_announcements()

    # Ensure "Git repo: none" present and no "Weak model" line
    assert any(l == "Git repo: none" for l in lines)
    assert not any(l.startswith("Weak model: ") for l in lines)
    # Repo-map disabled because map_tokens == 0
    assert any(l == "Repo-map: disabled because map_tokens == 0" for l in lines)
    # No restored previous conversation because done_messages is False
    assert not any("Restored previous conversation history." == l for l in lines)
    # Multiline mode not mentioned
    assert not any("Multiline mode: Enabled." in l for l in lines)
