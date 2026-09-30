# file: aider/coders/base_coder.py:299-542
# asked: {"lines": [362, 376, 410, 467, 468, 485, 488, 489, 520, 521, 522, 523, 535, 537, 538, 540, 541, 542], "branches": [[357, 360], [361, 362], [375, 376], [409, 410], [466, 467], [482, 485], [487, 488], [519, 520], [521, 522], [521, 526], [534, 535], [537, 538], [537, 540], [540, 0], [540, 541]]}
# gained: {"lines": [362, 376, 410, 467, 468, 485, 488, 489, 520, 521, 522, 523, 535, 537, 538, 540, 541, 542], "branches": [[361, 362], [375, 376], [409, 410], [466, 467], [482, 485], [487, 488], [519, 520], [521, 522], [534, 535], [537, 538], [537, 540], [540, 541]]}

import json
import os
import sys
import types
import pytest
from pathlib import Path
import importlib

# Import the module under test
bc = importlib.import_module("aider.coders.base_coder")
Coder = bc.Coder


class DummyCommands:
    def __init__(self, io, coder):
        self.io = io
        self.coder = coder


class DummyLinter:
    def __init__(self, root=None, encoding=None):
        self.root = root
        self.encoding = encoding


class DummyChatSummary:
    def __init__(self, models, max_tokens):
        self.models = models
        self.max_tokens = max_tokens


class DummyRepoMap:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class SimpleRepo:
    def __init__(self, root):
        self.root = str(root)

    def git_ignored_file(self, fname):
        # For tests, do not treat any file as git-ignored
        return False

    def ignored_file(self, fname):
        # For tests, do not treat any file as aider-ignored
        return False


class FakeIO:
    def __init__(self, chat_history_content=None):
        self.pretty = False
        self.encoding = "utf-8"
        self.tool_output_msgs = []
        self.tool_warning_msgs = []
        self.chat_history_file = "chat_history.md"
        self._read_text = chat_history_content

    def tool_output(self, *args):
        self.tool_output_msgs.append(" ".join(map(str, args)))

    def tool_warning(self, *args):
        self.tool_warning_msgs.append(" ".join(map(str, args)))

    def read_text(self, fname):
        return self._read_text


class DummyFileWatcher:
    def __init__(self):
        self.coder = None


class DummyMainModel:
    def __init__(self, *, reasoning_tag=None, streaming=True, cache_control=False, max_input_tokens=0, use_repo_map=False):
        self.reasoning_tag = reasoning_tag
        self.streaming = streaming
        self.cache_control = cache_control
        self.info = {"max_input_tokens": max_input_tokens}
        self.weak_model = object()
        self.max_chat_history_tokens = 1000
        self.use_repo_map = use_repo_map

    def commit_message_models(self):
        return []


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    # Patch external dependencies in the module to avoid side effects
    monkeypatch.setattr(bc, "Commands", DummyCommands)
    monkeypatch.setattr(bc, "Linter", DummyLinter)
    monkeypatch.setattr(bc, "ChatSummary", DummyChatSummary)
    monkeypatch.setattr(bc, "RepoMap", DummyRepoMap)
    # Ensure jsonschema check_schema is a no-op if jsonschema exists; otherwise inject fake module
    try:
        import jsonschema

        monkeypatch.setattr(jsonschema.Draft7Validator, "check_schema", lambda schema: None, raising=False)
    except Exception:
        fake_jsonschema = types.SimpleNamespace(Draft7Validator=types.SimpleNamespace(check_schema=lambda s: None))
        sys.modules["jsonschema"] = fake_jsonschema
    yield
    # cleanup potential injection
    if "jsonschema" in sys.modules and isinstance(sys.modules["jsonschema"], types.SimpleNamespace):
        del sys.modules["jsonschema"]


def test_init_with_file_watcher_aider_hashes_auto_commits_false_and_restore_history_and_functions_verbose(
    tmp_path, monkeypatch
):
    # Prepare environment
    tmp_dir = tmp_path
    # Create a directory to use as a fname that exists but is not a file
    dir_fname = tmp_dir / "somedir"
    dir_fname.mkdir()
    # Create a repo-like object to set root and avoid GitRepo usage
    repo = SimpleRepo(root=tmp_dir)

    # Fake chat history content to trigger restore_chat_history branch
    history_md = "### role: user\n- Hello"

    fake_io = FakeIO(chat_history_content=history_md)
    file_watcher = DummyFileWatcher()

    # Prepare a dummy summarize_start that sets a flag on the instance
    def summarize_start_flag(self):
        setattr(self, "summarize_started_flag", True)

    # Ensure we set functions on the class temporarily
    schema = {"type": "object"}  # trivial valid schema for jsonschema check

    # Patch summarize_start method and set functions on the class
    monkeypatch.setattr(bc.Coder, "summarize_start", summarize_start_flag)
    monkeypatch.setattr(bc.Coder, "functions", [schema], raising=False)

    # Create main model with use_repo_map False (so no RepoMap creation)
    main_model = DummyMainModel(reasoning_tag=None, streaming=True, cache_control=False, use_repo_map=False)

    # Prepare read-only filename that does NOT exist to hit the warning branch
    read_only_fname = "does_not_exist.txt"

    # Construct coder with map_tokens=None to hit map_tokens None branch and with auto_commits False
    coder = Coder(
        main_model=main_model,
        io=fake_io,
        repo=repo,
        fnames=[str(dir_fname)],
        read_only_fnames=[read_only_fname],
        file_watcher=file_watcher,
        aider_commit_hashes={"commit123"},
        auto_commits=False,
        map_tokens=None,
        restore_chat_history=True,
        verbose=True,
    )

    # Assertions for the various branches hit
    assert file_watcher.coder is coder, "file_watcher.coder should be set to the Coder instance (line 362)"
    assert coder.aider_commit_hashes == {"commit123"}
    assert coder.dirty_commits is False, "dirty_commits should be set False when auto_commits False (line 410)"
    # The directory should not have been added to abs_fnames because it is not a file
    assert all("somedir" not in p for p in coder.abs_fnames)
    # The read-only nonexistent file should have triggered a warning
    assert any("Read-only file" in msg or "does not exist" in msg for msg in fake_io.tool_warning_msgs)
    # restore_chat_history should populate done_messages and call summarize_start
    assert getattr(coder, "summarize_started_flag", False) is True
    assert isinstance(coder.done_messages, list)
    # functions verbose block should have produced "JSON Schema:" output
    assert any("JSON Schema" in msg for msg in fake_io.tool_output_msgs)

    # Cleanup: reset class-level functions attribute to avoid polluting other tests
    monkeypatch.setattr(bc.Coder, "functions", None, raising=False)


def test_init_map_tokens_else_branch_and_no_repo_map(tmp_path, monkeypatch):
    # Setup fake io and repo
    fake_io = FakeIO(chat_history_content=None)
    repo = SimpleRepo(root=tmp_path)

    # Patch Coder.functions to None to skip jsonschema block
    monkeypatch.setattr(bc.Coder, "functions", None, raising=False)

    main_model = DummyMainModel(streaming=True, cache_control=False, use_repo_map=True)

    # map_tokens provided as 0 -> else branch (use_repo_map = map_tokens > 0) should be False
    coder = Coder(
        main_model=main_model,
        io=fake_io,
        repo=repo,
        fnames=[],
        map_tokens=0,  # triggers the else branch (lines 488-489)
    )

    # Because map_tokens == 0, use_repo_map should be False and repo_map should not be created
    assert getattr(coder, "repo_map", None) is None
    # Basic sanity checks
    assert coder.repo.root == str(tmp_path)
    assert coder.main_model is main_model
