import types
import builtins

import aider.coders.base_coder as base_coder


class FakeEditor:
    def __init__(self, name, edit_format):
        self.name = name
        self.edit_format = edit_format


class FakeModel:
    def __init__(self, name, editor_name="ed", editor_edit_format="edfmt",
                 thinking_tokens=None, reasoning_effort=None,
                 caches_by_default=False, supports_assistant_prefill=False,
                 repo_map_tokens=0):
        self.name = name
        self.weak_model = self
        self.editor_model = FakeEditor(editor_name, editor_edit_format)
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


class FakeRepo:
    def __init__(self, rel_dir, tracked_files_count):
        self._rel_dir = rel_dir
        self._tracked_files_count = tracked_files_count

    def get_rel_repo_dir(self):
        return self._rel_dir

    def get_tracked_files(self):
        # return a list of the specified length
        return list(range(self._tracked_files_count))


class FakeRepoMap:
    def __init__(self, max_map_tokens, refresh):
        self.max_map_tokens = max_map_tokens
        self.refresh = refresh


class FakeIO:
    def __init__(self, multiline_mode=False):
        self.multiline_mode = multiline_mode


class FakeSelf:
    def __init__(self, **kwargs):
        # Default values to keep tests focused on branches we want to exercise
        self.main_model = kwargs.get("main_model")
        self.edit_format = kwargs.get("edit_format", "normal")
        self.add_cache_headers = kwargs.get("add_cache_headers", False)
        self.repo = kwargs.get("repo", None)
        self.repo_map = kwargs.get("repo_map", None)
        self.abs_read_only_fnames = kwargs.get("abs_read_only_fnames", [])
        self.done_messages = kwargs.get("done_messages", False)
        self.io = kwargs.get("io", FakeIO(False))
        self.get_inchat_relative_files_list = kwargs.get("inchat_files", [])

    def get_inchat_relative_files(self):
        return list(self.get_inchat_relative_files_list)

    def get_rel_fname(self, fname):
        # deterministic rel-name mapping for tests
        return f"rel/{fname.split('/')[-1]}"


def test_architect_and_readonly_and_done_round_115(monkeypatch):
    """Trigger the architect editor block, abs_read_only_fnames branch, done_messages and multiline mode."""
    # Patch version and urls to deterministic values
    monkeypatch.setattr(base_coder, "__version__", "0.TEST")
    monkeypatch.setattr(base_coder.urls, "large_repos", "https://example/large_repos")

    main_model = FakeModel("main", editor_name="editorX", editor_edit_format="architectfmt",
                           thinking_tokens=10, reasoning_effort=2)

    fs = FakeSelf(
        main_model=main_model,
        edit_format="architect",
        repo=None,
        repo_map=None,
        abs_read_only_fnames=["/abs/path/file1.txt"],
        done_messages=True,
        io=FakeIO(multiline_mode=True),
        inchat_files=["fileA.py"],
    )

    lines = base_coder.Coder.get_announcements(fs)

    # Assertions for expected branches
    # first line should include patched version
    assert lines[0] == "Aider v0.TEST"

    # architect editor block was added
    assert any("Editor model: editorX with architectfmt edit format" in l for l in lines), lines

    # abs_read_only_fnames should produce a read-only added line
    assert any("Added rel/file1.txt to the chat (read-only)." == l for l in lines), lines

    # done_messages should produce the restored history line
    assert any(l == "Restored previous conversation history." for l in lines), lines

    # multiline mode line should appear
    assert any(l.startswith("Multiline mode: Enabled") for l in lines), lines


def test_repo_large_and_repo_map_warning_round_115(monkeypatch):
    """Trigger large repo warning and repo-map > max_map_tokens warning."""
    monkeypatch.setattr(base_coder, "__version__", "0.TEST")
    # deterministic large repos URL
    monkeypatch.setattr(base_coder.urls, "large_repos", "https://example/large_repos")

    # create a main model that returns a small repo_map token value so max_map_tokens will be small
    main_model = FakeModel("main", repo_map_tokens=10)

    # Repo with > 1000 files
    repo = FakeRepo(rel_dir="/my/repo", tracked_files_count=1500)

    # RepoMap with tokens larger than allowed max_map_tokens (which will be main_model.get_repo_map_tokens()*2 = 20)
    repo_map = FakeRepoMap(max_map_tokens=100, refresh="24h")

    fs = FakeSelf(
        main_model=main_model,
        edit_format="normal",
        repo=repo,
        repo_map=repo_map,
        abs_read_only_fnames=[],
        done_messages=False,
        io=FakeIO(multiline_mode=False),
        inchat_files=[],
    )

    lines = base_coder.Coder.get_announcements(fs)

    # Check repo summary line
    assert any(l.startswith("Git repo: /my/repo with 1,500 files") for l in lines), lines

    # Large repo warning line should be present
    assert any("Warning: For large repos" in l for l in lines), lines

    # See large repos URL should be present
    assert any("See: https://example/large_repos" in l for l in lines), lines

    # Repo-map 'using' line should be present
    assert any(l.startswith("Repo-map: using 100 tokens, 24h refresh") for l in lines), lines

    # Map-tokens warning should be present (partial match ok because message is multi-line concatenation)
    assert any("Warning: map-tokens >" in l for l in lines), lines
