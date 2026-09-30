# file: aider/commands.py:445-551
# asked: {"lines": [469, 470, 488, 497, 498, 499, 501, 502, 503, 536, 541, 542, 543, 547, 548], "branches": [[468, 469], [476, 480], [487, 488], [496, 497], [499, 496], [499, 501], [535, 536], [539, 541], [541, 542], [541, 547]]}
# gained: {"lines": [469, 470, 488, 497, 498, 499, 501, 502, 503, 536, 541, 542, 543, 547, 548], "branches": [[468, 469], [487, 488], [496, 497], [499, 501], [535, 536], [539, 541], [541, 542], [541, 547]]}

import os
import pytest

from aider.commands import Commands
from aider.utils import is_image_file


class FakeIO:
    def __init__(self, read_map):
        self.read_map = read_map
        self.outputs = []
        self.errors = []

    def read_text(self, fname):
        # Return mapping by full path or basename
        return self.read_map.get(fname) or self.read_map.get(os.path.basename(fname))

    def tool_output(self, *args):
        if not args:
            self.outputs.append("")  # blank line
        else:
            # join args if multiple passed (unlikely in code)
            self.outputs.append("".join(str(a) for a in args))

    def tool_error(self, *args):
        self.errors.append("".join(str(a) for a in args))


class FakeMainModel:
    def __init__(self, info, name="fake-model"):
        self.info = info
        self.name = name

    def token_count(self, x):
        # Distinguish between system messages (list starting with role 'system'),
        # chat history (list starting with role not 'system'),
        # repo map strings containing 'REPO_MAP',
        # file contents by filename substrings.
        if isinstance(x, list):
            if x and isinstance(x[0], dict) and x[0].get("role") == "system":
                return 11  # system messages
            return 22  # chat history
        if isinstance(x, str):
            if "REPO_MAP" in x:
                return 33
            if "file.txt" in x:
                return 5
            if "readonly.txt" in x:
                return 6
            # fallback for other strings
            return max(1, len(x) // 10)
        return 0

    def token_count_for_image(self, fname):
        # return a distinct count for images
        return 77


class FakeRepoMap:
    def __init__(self, content):
        self._content = content

    def get_repo_map(self, abs_fnames, other_files):
        # Return content only when asked; mimic real behaviour
        return self._content


class FakeGptPrompts:
    def __init__(self):
        self.main_system = "main_system_prompt"
        self.system_reminder = "system_reminder"


class FakeCoder:
    def __init__(
        self,
        main_model,
        abs_fnames=None,
        abs_read_only_fnames=None,
        done_messages=None,
        cur_messages=None,
        repo_map=None,
        all_abs_files=None,
    ):
        self.main_model = main_model
        self.abs_fnames = abs_fnames or []
        self.abs_read_only_fnames = abs_read_only_fnames or []
        self.done_messages = done_messages or []
        self.cur_messages = cur_messages or []
        self.repo_map = repo_map
        self.gpt_prompts = FakeGptPrompts()
        self._all_abs_files = all_abs_files or set(self.abs_fnames + (self.abs_read_only_fnames or []))

    def choose_fence(self):
        # no-op for tests
        return

    def fmt_system_prompt(self, s):
        # return a recognizable string fragment
        return f"FMT:{s}"

    def get_all_abs_files(self):
        return list(self._all_abs_files)

    def get_rel_fname(self, fname):
        return os.path.basename(fname)


def make_fake_self(io_map, coder):
    """Create a fake 'self' object suitable for calling Commands.cmd_tokens(self, args)."""
    fake = type("FakeSelf", (), {})()
    fake.io = FakeIO(io_map)
    fake.coder = coder
    return fake


def test_cmd_tokens_large_remaining_triggers_remaining_gt_1024():
    # Prepare files: an image, a normal file, and a read-only file.
    abs_fnames = ["/repo/image.png", "/repo/file.txt"]
    abs_read_only_fnames = ["/repo/readonly.txt"]

    # Map file contents
    io_map = {
        "/repo/image.png": "PNGDATA",
        "/repo/file.txt": "some content of file.txt",
        "/repo/readonly.txt": "readonly content",
    }

    # main_model info with a large max_input_tokens to make remaining > 1024
    # We'll compute expected total based on FakeMainModel behavior:
    # system messages = 11
    # chat history (we'll include one done message) = 22
    # repo_map = 33
    # file.txt -> token_count returns 5
    # image.png -> token_count_for_image returns 77
    # readonly.txt -> token_count returns 6
    main_model = FakeMainModel(info={"max_input_tokens": 5000, "input_cost_per_token": 0.001}, name="fake")
    repo_map = FakeRepoMap("REPO_MAP content")
    coder = FakeCoder(
        main_model=main_model,
        abs_fnames=abs_fnames,
        abs_read_only_fnames=abs_read_only_fnames,
        done_messages=[{"role": "user", "content": "hi"}],
        cur_messages=[],
        repo_map=repo_map,
        all_abs_files=set(abs_fnames + abs_read_only_fnames),
    )
    fake = make_fake_self(io_map, coder)

    # Call the unbound method with our fake self
    Commands.cmd_tokens(fake, args=None)

    # Assertions: ensure outputs were produced and remaining > 1024 message present
    outputs = fake.io.outputs
    errors = fake.io.errors

    # Basic output checks
    assert any("Approximate context window usage for fake" in o for o in outputs), outputs
    # compute expected total tokens
    expected_total = 11 + 22 + 33 + 5 + 77 + 6
    # remaining = 5000 - expected_total (>1024)
    remaining = 5000 - expected_total
    assert remaining > 1024

    # There should be a line indicating tokens remaining in context window (tool_output)
    assert any("tokens remaining in context window" in o for o in outputs), outputs
    # No tool_error should have been called in this scenario
    assert not errors


def test_cmd_tokens_remaining_small_positive_uses_tool_error(monkeypatch):
    # Create a scenario where remaining is small positive (<=1024)
    abs_fnames = ["/repo/file.txt"]
    abs_read_only_fnames = []

    io_map = {"/repo/file.txt": "some content of file.txt"}

    # Build main_model with max_input_tokens such that remaining is small positive.
    # Using FakeMainModel semantics:
    # system=11, chat history=22, no repo_map, file.txt=5 => total = 38
    # set limit to 38 + 100 (<=1024)
    limit = 38 + 100
    main_model = FakeMainModel(info={"max_input_tokens": limit, "input_cost_per_token": 0.0}, name="fake2")
    coder = FakeCoder(
        main_model=main_model,
        abs_fnames=abs_fnames,
        abs_read_only_fnames=abs_read_only_fnames,
        done_messages=[{"role": "user", "content": "hi"}],
        cur_messages=[],
        repo_map=None,
        all_abs_files=set(abs_fnames),
    )
    fake = make_fake_self(io_map, coder)

    Commands.cmd_tokens(fake, args=None)

    # Expect that a tool_error was used to warn about low remaining tokens
    assert any("tokens remaining in context window (use /drop or /clear to make space)" in e for e in fake.io.errors)


def test_cmd_tokens_remaining_nonpositive_shows_exhausted_message():
    # Scenario where remaining <= 0
    abs_fnames = ["/repo/file.txt"]
    io_map = {"/repo/file.txt": "some content of file.txt"}

    # total from FakeMainModel: system 11 + chat 22 + file 5 = 38
    limit = 38  # remaining = 0 => exhausted
    main_model = FakeMainModel(info={"max_input_tokens": limit}, name="fake3")
    coder = FakeCoder(
        main_model=main_model,
        abs_fnames=abs_fnames,
        abs_read_only_fnames=[],
        done_messages=[{"role": "user", "content": "hi"}],
        cur_messages=[],
        repo_map=None,
        all_abs_files=set(abs_fnames),
    )
    fake = make_fake_self(io_map, coder)

    Commands.cmd_tokens(fake, args=None)

    # Should have produced a tool_error indicating window exhausted
    assert any("window exhausted" in e for e in fake.io.errors)
    # Also should output the max context window size at the end
    assert any("tokens max context window size" in o for o in fake.io.outputs)


def test_cmd_tokens_no_limit_returns_early():
    # Ensure the early return when max_input_tokens is falsy (0 or missing)
    abs_fnames = []
    io_map = {}

    # main_model.info has no max_input_tokens -> limit becomes 0 => early return
    main_model = FakeMainModel(info={}, name="fake4")
    coder = FakeCoder(
        main_model=main_model,
        abs_fnames=abs_fnames,
        abs_read_only_fnames=[],
        done_messages=[],
        cur_messages=[],
        repo_map=None,
        all_abs_files=set(),
    )
    fake = make_fake_self(io_map, coder)

    result = Commands.cmd_tokens(fake, args=None)

    # Since limit is falsy, cmd_tokens should return None (early return)
    assert result is None
    # But it should have produced some outputs for header and totals before returning
    assert any("Approximate context window usage for fake4" in o for o in fake.io.outputs)
