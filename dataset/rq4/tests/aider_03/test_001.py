import types

from aider.commands import Commands


class DummyModel:
    def __init__(self):
        # deterministic metadata used by cmd_tokens
        self.name = "dummy"
        self.info = {"input_cost_per_token": 0, "max_input_tokens": 0}
        # record every token_count call argument for inspection
        self.calls = []

    def token_count(self, arg):
        # record the exact argument passed (list or str) and return a deterministic number
        self.calls.append(arg)
        return 42

    def token_count_for_image(self, fname):
        # record image token_count usage distinctly
        self.calls.append(("image", fname))
        return 100


class DummyIO:
    def read_text(self, fname):
        # deterministic non-image file content without any backticks
        return "This is the file body. No fences here."

    def tool_output(self, *args, **kwargs):
        # no-op sink for prints
        pass

    def tool_error(self, *args, **kwargs):
        # no-op sink for errors
        pass


class DummyCoder:
    def __init__(self, model):
        self.main_model = model
        # simple prompts used by cmd_tokens; fmt_system_prompt will be called
        self.gpt_prompts = types.SimpleNamespace(main_system="MAIN", system_reminder="REM")
        self.fmt_system_prompt = lambda x: f"FMT:{x}"
        # choose_fence is called but cmd_tokens uses a local fence variable; keep no-op
        self.choose_fence = lambda: None
        # keep chat history empty to avoid extra token_count calls
        self.done_messages = []
        self.cur_messages = []
        # no repository map to avoid repo_map token_count path
        self.repo_map = None
        self.get_all_abs_files = lambda: []
        # include exactly one non-image absolute filename
        self.abs_fnames = ["/abs/path/example.md"]
        self.abs_read_only_fnames = []

    def get_rel_fname(self, fname):
        # return a stable relative filename used by cmd_tokens when building content
        return "example.md"


def test_probe_001():
    """
    Activation: run Commands.cmd_tokens with one deterministic non-image file.

    Oracle: the string passed to model.token_count for the file must include both
    opening and closing fence sequences of three backticks ("```"). The test
    inspects recorded token_count calls and asserts the candidate file string
    contains the closing fence (equivalently at least two occurrences of "```").
    """

    model = DummyModel()
    coder = DummyCoder(model)
    io = DummyIO()

    # Instantiate the public entrypoint (Commands) and call the focused method
    commands = Commands(io, coder)

    # Run the target unit; args value not relevant for this probe
    commands.cmd_tokens("")

    # Filter recorded token_count calls to those that are plain strings
    string_calls = [c for c in model.calls if isinstance(c, str)]

    # We expect at least one string argument (the file content built by cmd_tokens)
    assert string_calls, "no string content was passed to main_model.token_count"

    # Heuristic: choose the longest recorded string as the file-content candidate
    candidate = max(string_calls, key=len)

    # Primary oracle: the candidate must contain both opening and closing fence sequences
    assert candidate.count("```") >= 2, (
        "expected file content passed to token_count to include both opening and closing backtick fences '```'",
        candidate,
    )
