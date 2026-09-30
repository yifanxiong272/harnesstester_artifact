import types
from aider import commands


class FakeModel:
    def __init__(self, token_count_values=None, image_token_values=None, info=None):
        # queues of return values for token_count and token_count_for_image
        self._tc_values = list(token_count_values or [])
        self._img_values = list(image_token_values or [])
        self.info = dict(info or {})
        self.name = self.info.get("name", "fake-model")
        self.token_count_calls = []
        self.token_count_for_image_calls = []

    def token_count(self, content):
        self.token_count_calls.append(content)
        if self._tc_values:
            return self._tc_values.pop(0)
        # deterministic fallback
        if isinstance(content, list):
            return 1
        if isinstance(content, str):
            return max(1, len(content) // 10)
        return 1

    def token_count_for_image(self, fname):
        self.token_count_for_image_calls.append(fname)
        if self._img_values:
            return self._img_values.pop(0)
        return 5


class FakeRepoMap:
    def __init__(self, content=None):
        self._content = content
        self.get_repo_map_calls = []

    def get_repo_map(self, abs_fnames, other_files):
        self.get_repo_map_calls.append((tuple(abs_fnames), tuple(sorted(other_files))))
        return self._content


class FakeIO:
    def __init__(self, text_map=None):
        self.outputs = []
        self.errors = []
        self._text_map = dict(text_map or {})

    def tool_output(self, msg=""):
        # normalize to str for deterministic comparisons
        self.outputs.append(str(msg))

    def tool_error(self, msg):
        self.errors.append(str(msg))

    def read_text(self, fname):
        # return mapping or default small content
        return self._text_map.get(fname, "filecontent")


class DummyCoder:
    def __init__(self, model, abs_fnames=None, abs_read_only_fnames=None, repo_map=None, done_messages=None, cur_messages=None):
        self.main_model = model
        self.abs_fnames = list(abs_fnames or [])
        self.abs_read_only_fnames = list(abs_read_only_fnames or [])
        self.repo_map = repo_map
        self.done_messages = list(done_messages or [])
        self.cur_messages = list(cur_messages or [])
        # prompts container used by fmt_system_prompt
        self.gpt_prompts = types.SimpleNamespace(main_system="main", system_reminder="rem")

    def choose_fence(self):
        # no-op in tests
        return

    def fmt_system_prompt(self, placeholder):
        # just return the placeholder so callers get predictable strings
        return placeholder

    def get_all_abs_files(self):
        # include an extra file to be considered as other_files
        return set(self.abs_fnames) | {"/abs/other.txt"}

    def get_rel_fname(self, fname):
        # simple basename
        return fname.split("/")[-1]


def make_self(token_count_values, image_token_values, model_info, abs_fnames, abs_read_only_fnames, text_map, repo_content, done_messages, cur_messages):
    model = FakeModel(token_count_values=token_count_values, image_token_values=image_token_values, info=model_info)
    repo = FakeRepoMap(content=repo_content) if repo_content is not None else None
    coder = DummyCoder(model=model, abs_fnames=abs_fnames, abs_read_only_fnames=abs_read_only_fnames, repo_map=repo, done_messages=done_messages, cur_messages=cur_messages)
    io = FakeIO(text_map=text_map)
    dummy = types.SimpleNamespace()
    dummy.coder = coder
    dummy.io = io
    return dummy


# Patch is_image_file on the module where the function under test resolves it
def _patch_is_image(monkeypatch):
    # simple deterministic rule: names ending with .png or .jpg are images
    monkeypatch.setattr(commands, "is_image_file", lambda name: str(name).lower().endswith(('.png', '.jpg')))


def test_cmd_tokens_no_limit_round_074(monkeypatch):
    """
    Exercise the code path that collects system, chat, repo map, file tokens and read-only files,
    and returns early when max_input_tokens is falsy (covers lines around 469,476,487,496-503,535-536).
    """
    _patch_is_image(monkeypatch)

    # token_count call order: system, chat, repo, file text, read-only file
    token_values = [1, 2, 3, 11, 13]
    image_values = [7]  # for the image file

    model_info = {"input_cost_per_token": 0.01, "max_input_tokens": 0}

    abs_files = ['/abs/img.png', '/abs/code.py']
    read_only = ['/abs/readme.md']
    text_map = {
        '/abs/img.png': '<binary>',
        '/abs/code.py': 'print("hello")',
        '/abs/readme.md': 'README contents'
    }

    dummy = make_self(token_values, image_values, model_info, abs_files, read_only, text_map, repo_content="repo_map_text", done_messages=[{"role":"user","content":"hi"}], cur_messages=[])

    # Call the class function as an unbound function with our dummy self
    commands.Commands.cmd_tokens(dummy, args=None)

    # Validate outputs contain header and token lines and that we returned before remaining logic
    out = dummy.io.outputs
    # header line
    assert any("Approximate context window usage" in o for o in out), out
    # the repo map and files should have been reported
    assert any("repository map" in o for o in out), out
    assert any("img.png" in o for o in out), out
    assert any("code.py" in o for o in out), out
    # separator and total present
    assert any(o.strip().startswith("=") for o in out), out
    assert any("tokens total" in o for o in out), out
    # Since max_input_tokens was falsy, there should be no token-limit related errors
    assert dummy.io.errors == []

    # Ensure model methods were invoked as expected
    assert len(dummy.coder.main_model.token_count_calls) >= 4
    assert len(dummy.coder.main_model.token_count_for_image_calls) == 1


def test_cmd_tokens_remaining_large_round_074(monkeypatch):
    """
    Test branch where remaining > 1024; this should emit a tool_output with the "tokens remaining in context window" message (covers line 541).
    """
    _patch_is_image(monkeypatch)

    # Make every token_count small so total is small relative to limit
    token_values = [1, 1, 1, 1]  # system, chat, repo, single text file
    image_values = [2]
    model_info = {"input_cost_per_token": 0.0, "max_input_tokens": 5000}

    abs_files = ['/abs/img.png', '/abs/code.py']
    read_only = []
    text_map = {'/abs/img.png': '<binary>', '/abs/code.py': 'x'}

    dummy = make_self(token_values, image_values, model_info, abs_files, read_only, text_map, repo_content="repo", done_messages=[{"role":"user","content":"hey"}], cur_messages=[])

    commands.Commands.cmd_tokens(dummy, args=None)

    # Should find the remaining-large message in outputs
    assert any("tokens remaining in context window" in o for o in dummy.io.outputs), dummy.io.outputs
    # No errors should be emitted for remaining when it's large
    assert not dummy.io.errors


def test_cmd_tokens_remaining_small_and_exhausted_round_074(monkeypatch):
    """
    Verify both the "remaining small >0" and "exhausted" branches by manipulating max_input_tokens
    and token counts. This covers lines 542-545 and 547-550.
    """
    _patch_is_image(monkeypatch)

    # We'll first simulate a small remaining (>0 and <=1024)
    token_values_small_remaining = [10, 0, 0, 0]  # make total reasonably large
    image_values_small = [0]
    # Set limit slightly larger than total but under 1024
    model_info_small = {"input_cost_per_token": 0.0, "max_input_tokens": 1000}

    abs_files = ['/abs/code.py']
    read_only = []
    text_map = {'/abs/code.py': 'content'*10}

    dummy_small = make_self(token_values_small_remaining, image_values_small, model_info_small, abs_files, read_only, text_map, repo_content=None, done_messages=[{"role":"user","content":"hi"}], cur_messages=[])
    commands.Commands.cmd_tokens(dummy_small, args=None)

    # Now small remaining should produce a tool_error with guidance about /drop or /clear
    assert any("use /drop or" in e or "use /clear" in e for e in dummy_small.io.errors), dummy_small.io.errors

    # Now simulate exhausted (remaining <= 0)
    # Make token counts sum equal to limit so remaining == 0
    token_values_exhausted = [5, 5]  # system + chat
    image_values_exhausted = []
    # limit equals sum of token_values_exhausted
    model_info_exhausted = {"input_cost_per_token": 0.0, "max_input_tokens": sum(token_values_exhausted)}

    abs_files = []
    read_only = []
    dummy_ex = make_self(token_values_exhausted, image_values_exhausted, model_info_exhausted, abs_files, read_only, {}, repo_content=None, done_messages=[{"role":"user","content":"x"}], cur_messages=[])
    commands.Commands.cmd_tokens(dummy_ex, args=None)

    # exhausted should produce a tool_error complaining the window is exhausted
    assert any("window exhausted" in e or "window exhausted (use /drop or" in e for e in dummy_ex.io.errors), dummy_ex.io.errors
